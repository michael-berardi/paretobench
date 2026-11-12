"""Shared runner for both benches. Ported from the steak-dsh bench run.py with the
same behaviour: fresh fixture per run, private per-process work dir removed on exit,
stop flag and child process-group kill, hard timeout, balanced order, warm-up per lane,
an arm whose every warm-up fails aborts with a named error, resume from existing rows,
rate-limit retries, raw event logs via PB_LOG_DIR with keys scrubbed, failures kept as
incorrect runs. One rate table per model is applied to every harness (cost is computed
by report, never by a harness). Keys are passed only via the child env.
"""
import atexit
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import __version__
from . import config as C
from . import harnesses as H

WARM_PROMPT = "Reply with the single word ok."


def _die(name, msg):
    raise C.PBError(name, msg)


def build_entries(bench, models, ex, model=None, harness_names=None, harness=None,
                  model_keys=None, variants=None, registry=None):
    """Validate everything before anything runs. Returns a list of entry dicts."""
    get = (registry or {}).get if registry else H.get_adapter

    def adapter_for(name):
        a = get(name)
        if a is None:
            _die("unknown-harness", f"'{name}' (harnesses: {', '.join(H.ARM_MAP.values())})")
        return a

    variants = variants or {}
    entries = []
    if bench == "harness":
        if model not in models:
            _die("unknown-model", f"'{model}' not in models config (have: {', '.join(models)})")
        mcfg = models[model]
        names = list(harness_names)
        for vname, (base, _patch) in variants.items():
            if vname in names:
                _die("bad-variant", f"variant name '{vname}' collides with an existing harness")
            names.append(vname)
        for n in names:
            if n in variants:
                base, patch = variants[n]
                if base not in ("dsh", "steak-dsh"):
                    _die("bad-variant", f"variant '{n}': patches are only supported on dsh and steak-dsh, not '{base}'")
                if not os.path.isfile(patch):
                    _die("variant-patch-missing", f"variant '{n}': {patch}")
                a = adapter_for(base)
                entries.append(dict(name=n, harness=n, base=base, model=model, mcfg=mcfg,
                                    adapter=a, extra_patches=(patch,)))
            else:
                if n not in mcfg.get("harnesses", []):
                    _die("harness-unavailable-for-model",
                         f"model '{model}' does not list harness '{n}' (has: {', '.join(mcfg.get('harnesses', []))})")
                a = adapter_for(n)
                entries.append(dict(name=n, harness=n, base=n, model=model, mcfg=mcfg,
                                    adapter=a, extra_patches=()))
    elif bench == "model":
        names = list(model_keys)
        for mk in names:
            if mk not in models:
                _die("unknown-model", f"'{mk}' not in models config (have: {', '.join(models)})")
            mcfg = models[mk]
            if harness not in mcfg.get("harnesses", []):
                _die("harness-unavailable-for-model",
                     f"model '{mk}' does not list harness '{harness}' (has: {', '.join(mcfg.get('harnesses', []))})")
            entries.append(dict(name=mk, harness=harness, base=harness, model=mk, mcfg=mcfg,
                                adapter=adapter_for(harness), extra_patches=()))
    else:
        _die("unknown-bench", f"'{bench}' (benches: harness, model)")
    if len(set(e["name"] for e in entries)) != len(entries):
        _die("duplicate-entry", "entry names must be unique")
    for e in entries:
        e["adapter"].validate(e["mcfg"], ex)
    return entries


def run_bench(bench, entries, reps, par, out_dir, task_names=None, timeout=None, ex=None, task_set=None):
    """Run the bench. entries come from build_entries. Rows go to <out_dir>/rows.jsonl.
    timeout: hard per-run seconds for every task; None means the task set's budgets.json, else 600."""
    ex = ex or C.resolve_executables()
    td = C.tasks_dir(task_set)
    budgets = C.task_budgets(td)

    def budget(task):
        if timeout is not None:
            return timeout
        return budgets.get(task, budgets.get("default", C.DEFAULT_TIMEOUT))
    tasks = C.validate_tasks(td)
    tset = C.task_set_hash(td)
    names = list(task_names) if task_names else list(tasks)
    for t in names:
        if t not in tasks:
            _die("unknown-task", f"'{t}' not in {td}/tasks.json")

    # --- keys: read once, passed only via child env, scrubbed from every output ---
    key_vals = []
    for e in entries:
        e["key_env"] = e["key_val"] = None
        if getattr(e["adapter"], "needs_key", False):
            ks = e["mcfg"]["key"]
            e["key_env"] = ks["env"]
            e["key_val"] = C.load_auth_key(ex["pi_agent_dir"], ks["auth"])
            key_vals.append(e["key_val"])

    def scrub(s):
        for v in key_vals:
            if v:
                s = s.replace(v, "***")
        return s

    # --- one private work dir per runner process, removed on exit (Steak Pi lanes
    # hold a copy of the auth store). Two concurrent runs never share fixtures. ---
    base = os.path.join(tempfile.gettempdir(), "paretobench")
    os.makedirs(base, exist_ok=True)
    work = tempfile.mkdtemp(prefix=f"run-{os.getpid()}-", dir=base)
    os.chmod(work, 0o700)
    live = set()
    live_lock = threading.Lock()
    stopping = threading.Event()  # set first on a stop: no new child, no new fixture, no result row after it

    def cleanup():
        with live_lock:
            pids = list(live)
        for pid in pids:
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        shutil.rmtree(work, ignore_errors=True)

    def on_signal(signum, _frame):
        stopping.set()
        print(f"stopped by signal {signum}: killing {len(live)} child process group(s)", file=sys.stderr, flush=True)
        cleanup()
        time.sleep(0.3)  # let worker threads observe the stop before the last sweep
        shutil.rmtree(work, ignore_errors=True)
        os._exit(128 + signum)

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    spec = importlib.util.spec_from_file_location("pb_gen_fixture", os.path.join(td, "gen_fixture.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prepare = mod.prepare
    checker = os.path.join(td, "checks", "check.py")
    # a task set whose generator takes (dest, task) builds a per-task fixture (the long set does)
    import inspect
    per_task_fixture = len(inspect.signature(prepare).parameters) >= 2

    def fresh(entry_name, slot, task=None):
        if stopping.is_set():
            raise H.RunFail("runner stopped", "", "")
        d = os.path.join(work, "work", f"{entry_name}-{slot}")
        shutil.rmtree(d, ignore_errors=True)
        if per_task_fixture:
            prepare(d, task)
        else:
            prepare(d)
        return d

    # --- generated dsh model patch per model (two rows) ---
    patch_files = {}
    for e in entries:
        if e["adapter"].family == "dsh" and e["model"] not in patch_files:
            dsh_cfg = e["mcfg"]["dsh"]
            pf = os.path.join(work, "patches", f"model-{e['model']}.yml")
            os.makedirs(os.path.dirname(pf), exist_ok=True)
            sel = {"provider": dsh_cfg["provider"], "model": dsh_cfg["model"]}
            if dsh_cfg.get("reasoningEffort"):
                sel["reasoningEffort"] = dsh_cfg["reasoningEffort"]
            patch = [
                {"id": "llm-pi-ai", "name": "@deepseek-ai/dsh-llm-pi-ai",
                 "config": {"providers": {dsh_cfg["provider"]: dsh_cfg["route"]}}},
                {"id": "agent-default-model", "name": "@deepseek-ai/dsh-agent-default-model", "config": sel},
            ]
            with open(pf, "w") as f:
                f.write(C.to_yaml(patch))
            patch_files[e["model"]] = pf

    # --- harness versions (no model calls) ---
    versions = {}
    for e in entries:
        if e["base"] not in versions:
            try:
                versions[e["base"]] = e["adapter"].version(ex)
            except C.PBError:
                raise
            except Exception as err:
                _die("harness-version-failed", f"harness '{e['base']}': {err!r}")

    # --- child process helper: hard timeout kills the whole process group ---
    def child(cmd, cwd, env, tmo):
        with live_lock:  # spawn and register under one lock, so a stop sees every child that exists
            if stopping.is_set():
                raise H.RunFail("runner stopped", "", "")
            p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
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

    # PB_LOG_DIR=<dir> keeps each run's raw event stream (keys scrubbed) as
    # <entry>-<task>-<rep>.jsonl for analysis.
    log_dir = os.environ.get("PB_LOG_DIR")
    last_log = {}

    def keep_log(entry_name, slot, out, err):
        if log_dir:
            last_log[(entry_name, slot)] = scrub(out or "") + (
                "\n#stderr\n" + scrub(err or "")[-4000:] if err else "")

    def run_entry(e, slot, cwd, prompt, tmo):
        a = e["adapter"]
        lane = a.setup_lane(ex, e["mcfg"], work, slot, e["name"])
        cmd, env_extra = a.build_command(ex, e["mcfg"], prompt, lane,
                                         model_patch=patch_files.get(e["model"]),
                                         extra_patches=e["extra_patches"])
        env = {**os.environ, **env_extra}
        if e["key_env"]:
            env[e["key_env"]] = e["key_val"]
        try:
            rc, out, err = child(cmd, cwd, env, tmo)
        except H.RunFail as fail:
            # A run killed at the hard timeout is the one whose event stream matters most: keep what it wrote.
            keep_log(e["name"], slot, getattr(fail, "out", ""), getattr(fail, "err", "") or str(fail))
            raise
        finally:
            a.after_run(lane)
        keep_log(e["name"], slot, out, err)
        return a.parse(rc, out, err, scrub)

    def rate_limited(blob):
        return bool(re.search(r"(?<!\d)429(?!\d)", blob)) or "RATE_LIMIT" in blob

    def invoke(e, slot, prompt, task=None, tmo=C.DEFAULT_TIMEOUT):
        """One attempt per fresh fixture, with rate-limit retries (30 s, then 90 s; at most 2).
        Returns (u, text, err, retries, cwd)."""
        retries = 0
        while True:
            cwd = fresh(e["name"], slot, task)
            try:
                u, text = run_entry(e, slot, cwd, prompt, tmo)
                return u, text, "", retries, cwd
            except Exception as err:
                blob = scrub(str(err) + getattr(err, "out", "")[-4000:] + getattr(err, "err", "")[-4000:])
                if retries < 2 and rate_limited(blob):
                    time.sleep(30 if retries == 0 else 90)
                    retries += 1
                    continue
                return {}, "", scrub(repr(err))[:200], retries, cwd

    out_dir = os.path.abspath(os.path.expanduser(out_dir))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "rows.jsonl")
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                aname = r.get("arm")
                ename = H.ARM_MAP.get(aname, aname) if aname else r.get("harness")
                done.add((ename, r.get("model"), r["task"], r["rep"]))

    entry_list = list(entries)
    jobs = []
    for rep in range(reps):
        for ti, t in enumerate(names):
            order = entry_list[(rep + ti) % len(entry_list):] + entry_list[:(rep + ti) % len(entry_list)]
            for e in order:
                if (e["name"], e["model"], t, rep) not in done:
                    jobs.append((rep, t, e))
    if not jobs:
        print(f"nothing to do: all {len(done)} requested rows already in {out_path}", flush=True)
        return out_path

    lock = threading.Lock()
    chk_timeout = 120 if (task_set or C.DEFAULT_TASK_SET) == C.DEFAULT_TASK_SET else 900  # long checkers run suites and mutants

    def one(rep, task, e, slot):
        if stopping.is_set():
            return
        t0 = time.time()
        u, text, err, retries, d = invoke(e, slot, tasks[task], task, budget(task))
        if stopping.is_set():
            return  # a run cut short by a stop is not a result: it is run again on resume
        with open(os.path.join(d, "ans.txt"), "w") as f:
            f.write(text)
        if log_dir and (e["name"], slot) in last_log:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, f"{e['name']}-{task}-{rep}.jsonl"), "w") as f:
                f.write(last_log.pop((e["name"], slot)))
        chk_err, chk = "", False
        try:
            c = subprocess.run([sys.executable, checker, task, "ans.txt"], cwd=d,
                               capture_output=True, text=True, timeout=chk_timeout)
            chk = c.stdout.strip() == "true"
            if not chk:
                chk_err = scrub(c.stderr.strip())[:200]
        except Exception as err:
            chk_err = scrub(repr(err))[:200]
        row = dict(arm=e["name"], bench=bench, harness=e["harness"], model=e["model"],
                   task=task, rep=rep, ok=(not err and chk),
                   sec=round(time.time() - t0, 1),
                   i=u.get("i", 0), cr=u.get("cr", 0), cw=u.get("cw", 0), o=u.get("o", 0),
                   reasoning=u.get("reasoning", 0), turns=u.get("turns", 0), tools=u.get("tools", 0),
                   err=err, chk_err=chk_err, retries=retries,
                   harness_version=versions.get(e["base"], ""), pb_version=__version__,
                   task_set=tset, ts=round(time.time()))
        if bench == "harness" and e["base"] != e["name"]:
            row["variant_of"] = e["base"]
        with lock:
            if stopping.is_set():
                return
            with open(out_path, "a") as f:
                f.write(json.dumps(row) + "\n")
                f.flush()
            print(json.dumps(row), flush=True)

    slots = {e["name"]: queue.Queue() for e in entry_list}
    for e in entry_list:
        for k in range(par):
            slots[e["name"]].put(k)

    def job(x):
        rep, task, e = x
        k = slots[e["name"]].get()
        try:
            one(rep, task, e, k)
        finally:
            slots[e["name"]].put(k)

    def warm(x):
        e, k = x
        _, _, err, _, _ = invoke(e, k, WARM_PROMPT)
        if err:
            print(f"warm-up failed for {e['name']} lane {k}: {err}", file=sys.stderr, flush=True)
        return e["name"], err

    with ThreadPoolExecutor(par * len(entry_list)) as pool:
        warmed = list(pool.map(warm, [(e, k) for e in entry_list for k in range(par)]))
    # An arm that cannot answer one trivial request is misconfigured: stop before it
    # fills the results with failures.
    for e in entry_list:
        errs = [err for n, err in warmed if n == e["name"]]
        if errs and all(errs):
            _die("arm-cannot-run", f"every warm-up of arm '{e['name']}' failed: {errs[0]}")
    with ThreadPoolExecutor(par * len(entry_list)) as pool:
        list(pool.map(job, jobs))
    return out_path
