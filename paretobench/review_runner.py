"""Live runner for the review bench.

One reviewer call per case and repeat, staged in a fresh random workspace holding
only diff.patch and context/. case.json never reaches the reviewer. Existing rows are
resumed; a hard timeout kills the whole child process group; raw logs, when PB_LOG_DIR
is set, are scrubbed before being written. Keys come from the Pi auth store through the
harness adapter's private lane, never from this module's argv or rows.
"""
import atexit
import json
import os
import queue
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import __version__
from . import config as C
from . import harnesses as H
from . import review as RV

# The same neutral task text for every arm: no hint that some changes are clean,
# no mention of false alarms, no coaching. The verdict must be the last line.
REVIEW_PROMPT = (
    "Review a code change. The unified diff is in diff.patch in the current directory, "
    "and the files as they are after the change are under context/ (you may read any of them).\n"
    "Decide whether the change introduces a bug.\n"
    "End your reply with exactly one line in one of these two forms, and nothing after it:\n"
    "VERDICT: clean\n"
    "VERDICT: bug <path>:<line>\n"
    "where <path> is the file's path relative to context/ and <line> is the line number "
    "of the bug in that file after the change."
)
SUPPORTED = ("pi", "steak-pi", "claude-code")



def inline_model(model_id, harness):
    """A model named on the command line instead of in the models config.

    No route or key is stored here: pi and claude-code read their own auth store.
    It has no rate table, so its rows are compared in tokens, never shown as $0.
    """
    return {"harnesses": [harness], "pi": ["--model", model_id],
            "claude": ["--model", model_id], "rates": None}


def stage(case, root):
    """Copy only what a reviewer may see, into a directory named by random bytes."""
    workspace = os.path.join(root, secrets.token_hex(8))
    os.mkdir(workspace, 0o700)
    os.chmod(workspace, 0o700)
    shutil.copy2(os.path.join(case.directory, "diff.patch"), os.path.join(workspace, "diff.patch"))
    # Bytecode caches embed their compile-time path (which names the case), so they never reach the reviewer.
    shutil.copytree(os.path.join(case.directory, "context"), os.path.join(workspace, "context"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return workspace


def run(models, ex, harness, model, model_id, reps, par, out_dir,
        case_ids=None, timeout=600, registry=None, verbose=True):
    """Run the review bench and write rows.jsonl. Returns the output directory."""
    if harness not in SUPPORTED:
        raise C.PBError("review-harness-unsupported",
                        f"'{harness}' (review runs read-only tools; supported: {', '.join(SUPPORTED)})")
    get = (registry or {}).get if registry else H.get_adapter
    adapter = get(harness)
    if adapter is None:
        raise C.PBError("unknown-harness", f"'{harness}'")
    if not callable(getattr(adapter, "review_command", None)):
        raise C.PBError("review-harness-unsupported", f"'{harness}' has no read-only review command")
    if model_id:
        mcfg = inline_model(model_id, harness)
        label = f"{harness}/{model_id}"
    else:
        if model not in models:
            raise C.PBError("unknown-model", f"'{model}' not in models config (have: {', '.join(models)})")
        mcfg = models[model]
        if harness not in mcfg.get("harnesses", []):
            raise C.PBError("harness-unavailable-for-model",
                            f"model '{model}' does not list harness '{harness}'")
        label = f"{harness}/{model}"
    adapter.validate(mcfg, ex)
    version = adapter.version(ex)

    cases = RV.load_corpus()
    names = list(case_ids) if case_ids else sorted(cases)
    for name in names:
        if name not in cases:
            raise C.PBError("review-unknown-case", f"'{name}' is not in {C.REVIEW_TASK_SET}")
    tset = C.REVIEW_TASK_SET + ":" + corpus_hash()

    out_dir = os.path.abspath(os.path.expanduser(out_dir))
    C.private_dir(out_dir)
    rows_path = os.path.join(out_dir, "rows.jsonl")
    done = set()
    if os.path.isfile(rows_path):
        with open(rows_path) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue  # torn last line from an interrupted run; that row runs again
                if r.get("bench") == "review" and r.get("task_set") and r.get("task_set") != tset:
                    raise C.PBError("review-corpus-changed",
                                    f"{rows_path} has rows from {r.get('task_set')}, this corpus is {tset}; use a new --out")
                # A row that failed to produce a verdict because the run itself failed is retried on resume.
                if r.get("arm") == label and not (r.get("outcome") == "no_verdict" and r.get("err")):
                    done.add((r.get("task"), r.get("rep")))

    jobs = [(rep, name) for rep in range(reps) for name in names
            if (name, rep) not in done]
    if not jobs:
        if verbose:
            print(f"nothing to do: all {len(done)} requested rows for {label} are in {rows_path}", flush=True)
        report(out_dir, models, mcfg, label, verbose=verbose)
        return out_dir

    base = os.path.join(tempfile.gettempdir(), "paretobench-review")
    C.private_dir(base)
    work = tempfile.mkdtemp(prefix=f"review-{os.getpid()}-", dir=base)
    os.chmod(work, 0o700)
    os.makedirs(os.path.join(work, "work"))
    atexit.register(lambda: shutil.rmtree(work, ignore_errors=True))
    live, live_lock = set(), threading.Lock()

    def kill_live():
        with live_lock:
            pids = list(live)
        for pid in pids:
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    atexit.register(kill_live)

    def scrub(s):
        # pi-family keys live in the private lane's auth.json; keep the same
        # scrubber used for rows and logs in case a harness echoes one.
        key_vals = []
        auth = os.path.join(ex.get("pi_agent_dir") or "", "auth.json")
        try:
            with open(auth) as f:
                for entry in json.load(f).values():
                    if isinstance(entry, dict) and entry.get("key"):
                        key_vals.append(entry["key"])
        except (OSError, ValueError):
            pass
        for value in key_vals:
            s = str(s).replace(value, "***")
        return s

    def child(cmd, cwd, env, tmo):
        with live_lock:
            p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, start_new_session=True)
            live.add(p.pid)
        try:
            try:
                out, err = p.communicate(timeout=tmo)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                out, err = p.communicate()
                raise H.RunFail(f"timeout after {tmo}s", out or "", err or "")
        finally:
            with live_lock:
                live.discard(p.pid)
        return p.returncode, out, err

    log_dir = os.environ.get("PB_LOG_DIR")
    if log_dir:
        C.log_keep()  # refuse a bad retention bound before any model call

    def log_path(name, rep):
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", label)
        return os.path.join(log_dir, f"{safe}-{name}-{rep}.jsonl")

    def keep_log(name, rep, out, err):
        if not log_dir:
            return
        C.private_dir(log_dir)
        with C.private_open(log_path(name, rep)) as f:
            f.write(scrub(out or ""))
            if err:
                f.write("\n#stderr\n" + scrub(err)[-4000:])
        C.prune_logs(log_dir)

    def one(rep, name, slot):
        case = cases[name]
        started = time.time()
        workspace = stage(case, os.path.join(work, "work"))
        lane = adapter.setup_lane(ex, mcfg, work, slot, label)
        try:
            cmd, env_extra = adapter.review_command(ex, mcfg, REVIEW_PROMPT, lane)
            env = C.child_env(env_extra)
            rc, out, err = child(cmd, workspace, env, timeout)
            u, text = adapter.parse(rc, out, err, scrub)
            err_text = ""
            keep_log(name, rep, out, err)
        except Exception as e:
            u, text = {}, ""
            err_text = scrub(repr(e) + " " + (getattr(e, "err", "") or ""))[:400]
            keep_log(name, rep, getattr(e, "out", ""), err_text)
        finally:
            adapter.after_run(lane)
        verdict = RV.extract_verdict(text)
        row = {
            "bench": "review", "arm": label, "harness": harness,
            "model": model_id or model, "task": name, "rep": rep,
            "output": scrub(text), "verdict": verdict.kind, "vpath": verdict.path,
            "vline": verdict.line, "reason": verdict.reason,
            "outcome": RV.grade(case, verdict),
            "usage": {k: u.get(k, 0) for k in ("i", "cr", "cw", "o")},
            "i": u.get("i", 0), "cr": u.get("cr", 0), "cw": u.get("cw", 0), "o": u.get("o", 0),
            "reasoning": u.get("reasoning", 0), "turns": u.get("turns", 0), "tools": u.get("tools", 0),
            "err": err_text, "sec": round(time.time() - started, 1),
            "harness_version": version, "pb_version": __version__,
            "task_set": tset, "ts": round(time.time()),
        }
        with lock:
            with C.private_open(rows_path, append=True) as f:
                f.write(json.dumps(row) + "\n")
                f.flush()
        if verbose:
            print(f"{name} rep {rep}: {row['outcome']}", flush=True)

    lock = threading.Lock()
    slots = queue.Queue()
    for k in range(par):
        slots.put(k)

    def job(work_item):
        rep, name = work_item
        slot = slots.get()
        try:
            one(rep, name, slot)
        finally:
            slots.put(slot)

    if verbose:
        print(f"review: {len(jobs)} runs, {label}, model {model_id or model}, "
              f"{len(cases)} cases x {reps} reps (resume skips finished rows)", flush=True)
    try:
        with ThreadPoolExecutor(par) as pool:
            list(pool.map(job, jobs))
    finally:
        kill_live()
    report(out_dir, models, mcfg, label, verbose=verbose)
    return out_dir


def corpus_hash():
    """Short digest of the review corpus, so rows from changed cases are not mixed."""
    import hashlib
    h = hashlib.sha256()
    root = RV.corpus_dir()
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(base, name), root)
            with open(os.path.join(base, name), "rb") as f:
                h.update(rel.encode() + b"\0" + f.read() + b"\0")
    return h.hexdigest()[:16]


def report(out_dir, models=None, mcfg=None, label=None, verbose=True):
    """Print the review table and write summary.json / summary.md."""
    rows = RV.read_rows(out_dir)
    rates = {}
    for r in rows:
        arm = r.get("arm")
        if arm in rates:
            continue
        table = (mcfg or {}).get("rates") if label and arm == label else None
        if table is None and models:
            table = (models.get(r.get("model")) or {}).get("rates")
        rates[arm] = table
    rates = {arm: t for arm, t in rates.items() if t}
    graded = RV.grade_rows(rows, RV.load_corpus())
    summary = RV.summarize(graded, rates)
    text = RV.render(summary, md=False)
    if verbose:
        print(text)
    RV.write_reports(summary, out_dir)
    return summary
