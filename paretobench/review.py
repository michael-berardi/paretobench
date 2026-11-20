"""The review bench: corpus validation, verdict grading and the report.

A review run is graded from the reviewer's final text alone. The same code grades a
live row and a hand-written recorded-verdicts fixture, so the offline selftest covers
the grading path that live runs use. No model is called from this module.

The corpus in tasks/review-v1/corpus/ is adapted from oh-my-hermes' review-false-alarms
corpus (MIT); see tasks/review-v1/README.md for attribution and the case corrections.
"""
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass

from . import __version__
from . import config as C
from . import stats as ST

RECORDS_SCHEMA = "paretobench/review-records/v1"
MIN_RUNS = 3
LOCATION_WINDOW = 3
KINDS = ("trap", "control")
EXPECTED = {"trap": "clean", "control": "bug"}
BASE_KEYS = {"id", "kind", "language", "expected", "why"}
CASE_KEYS = BASE_KEYS | {"bug_location"}
TRAP_OUTCOMES = ("clean_ok", "false_alarm", "no_verdict")
CONTROL_OUTCOMES = ("hit", "miss_clean", "miss_location", "no_verdict")
DEFAULT_FIXTURE = os.path.join("fixtures", "recorded-verdicts.json")

_VERDICT = re.compile(r"^VERDICT:\s*(.*?)\s*$")
_BUG = re.compile(r"^bug\s+(\S+):([1-9][0-9]*)$")
_PATH_PREFIX = ("./", "context/", "a/", "b/")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def corpus_dir():
    """Directory holding the case directories (not the task set's fixtures)."""
    return os.path.join(C.tasks_dir(C.REVIEW_TASK_SET), "corpus")


def fixture_path():
    return os.path.join(os.path.dirname(corpus_dir()), DEFAULT_FIXTURE)


@dataclass(frozen=True)
class Case:
    id: str
    kind: str
    language: str
    why: str
    bug_path: str | None
    bug_line: int | None
    directory: str

    @property
    def expected(self):
        return EXPECTED[self.kind]


@dataclass(frozen=True)
class Verdict:
    kind: str  # clean, bug or none
    path: str | None = None
    line: int | None = None
    reason: str | None = None


def _bad(msg):
    raise C.PBError("review-corpus-invalid", msg)


def case_from_record(record, directory):
    """Validate one case.json object and return a Case."""
    name = os.path.basename(os.path.normpath(directory))
    if not isinstance(record, dict):
        _bad(f"{name}: case.json is not an object")
    kind = record.get("kind")
    if kind not in KINDS:
        _bad(f"{name}: kind must be trap or control, got {kind!r}")
    keys = CASE_KEYS if kind == "control" else BASE_KEYS
    if set(record) != keys:
        _bad(f"{name}: case.json keys {sorted(record)} != {sorted(keys)}")
    for field in ("id", "language", "why"):
        if not isinstance(record[field], str) or not record[field].strip():
            _bad(f"{name}: {field} must be a non-empty string")
    if record["id"] != name:
        _bad(f"{name}: id {record['id']!r} differs from the directory name")
    if record["expected"] != EXPECTED[kind]:
        _bad(f"{name}: a {kind} expects {EXPECTED[kind]!r}, got {record['expected']!r}")
    bug_path = bug_line = None
    if kind == "control":
        loc = record["bug_location"]
        if not isinstance(loc, dict) or set(loc) != {"path", "line"}:
            _bad(f"{name}: bug_location must be {{path, line}}")
        if not isinstance(loc["path"], str) or not loc["path"].strip():
            _bad(f"{name}: bug_location.path must be a non-empty string")
        if type(loc["line"]) is not int or loc["line"] < 1:
            _bad(f"{name}: bug_location.line must be a positive integer")
        bug_path, bug_line = loc["path"], loc["line"]
    return Case(record["id"], kind, record["language"], record["why"],
                bug_path, bug_line, directory)


def load_case(directory):
    for needed in ("case.json", "diff.patch", "context"):
        if not os.path.exists(os.path.join(directory, needed)):
            _bad(f"{os.path.basename(directory)}: missing {needed}")
    try:
        with open(os.path.join(directory, "case.json")) as f:
            record = json.load(f)
    except ValueError as e:
        _bad(f"{directory}: case.json: {e}")
    return case_from_record(record, directory)


def load_corpus(root=None):
    """Load every case directory. Structural checks only; use validate_corpus for patches too."""
    root = root or corpus_dir()
    if not os.path.isdir(root):
        _bad(f"corpus directory missing: {root}")
    cases = {}
    for name in sorted(os.listdir(root)):
        directory = os.path.join(root, name)
        if os.path.isdir(directory):
            case = load_case(directory)
            cases[case.id] = case
    if not cases:
        _bad(f"no cases in {root}")
    return cases


def parse_patch(text, case_id):
    """Parse a unified diff into [(path, hunks)] with hunk line/count checks."""
    files, path, hunk = [], None, None
    for line in text.splitlines(keepends=True):
        if line.startswith("--- a/"):
            path = line[6:].rstrip("\n")
            files.append((path, []))
            hunk = None
        elif line.startswith("+++ b/"):
            if path is None or line[6:].rstrip("\n") != path:
                _bad(f"{case_id}: patch +++ header does not match --- header")
        elif line.startswith("@@ "):
            m = _HUNK.match(line)
            if not m or path is None:
                _bad(f"{case_id}: bad hunk header {line.strip()!r}")
            hunk = {"old": int(m.group(1)), "new": int(m.group(3)),
                    "old_n": int(m.group(2) or 1), "new_n": int(m.group(4) or 1), "body": []}
            files[-1][1].append(hunk)
        elif hunk is not None and line.startswith((" ", "+", "-")):
            hunk["body"].append(line)
    for path, hunks in files:
        if not hunks:
            _bad(f"{case_id}: patch for {path} has no hunks")
        for h in hunks:
            old = [l[1:] for l in h["body"] if l[0] in " -"]
            new = [l[1:] for l in h["body"] if l[0] in " +"]
            if len(old) != h["old_n"] or len(new) != h["new_n"]:
                _bad(f"{case_id}: {path} hunk line counts do not match its headers")
            if h["old"] < 1 or h["new"] < 1:
                _bad(f"{case_id}: {path} hunk line numbers must be positive")
    return files


def patch_preimage(text, case_id, context_lines_by_path):
    """Rebuild the pre-change file from the patch and its post-change context.

    Every context and '+' line must appear in the context file exactly where the
    hunk says it does. This catches stale line numbers and patches that do not
    describe the context the reviewer is given.
    """
    pre = {}
    for path, hunks in parse_patch(text, case_id):
        if path not in context_lines_by_path:
            _bad(f"{case_id}: patch names {path}, absent from context/")
        new_lines = context_lines_by_path[path]
        old_lines, cursor = [], 0
        for h in hunks:
            start = h["new"] - 1
            new_chunk = [l[1:] for l in h["body"] if l[0] in " +"]
            if start < cursor or new_lines[start:start + len(new_chunk)] != new_chunk:
                _bad(f"{case_id}: {path} hunk at +{h['new']} does not match context/")
            old_lines.extend(new_lines[cursor:start])
            old_lines.extend(l[1:] for l in h["body"] if l[0] in " -")
            cursor = start + len(new_chunk)
        old_lines.extend(new_lines[cursor:])
        if not old_lines:
            _bad(f"{case_id}: {path} pre-image is empty")
        pre[path] = old_lines
    return pre


def validate_corpus(root=None):
    """Validate all cases, bug locations and patch/context consistency.

    Returns a small dict of counts for the CLI. Raises PBError with a named cause.
    """
    cases = load_corpus(root)
    root = root or corpus_dir()
    languages = defaultdict(int)
    for case in cases.values():
        languages[case.language] += 1
        context = os.path.join(case.directory, "context")
        if not os.path.isdir(context):
            _bad(f"{case.id}: context/ is not a directory")
        files = {}
        for base, _dirs, names in os.walk(context):
            _dirs[:] = [d for d in _dirs if d != "__pycache__"]
            names = [n for n in names if not n.endswith(".pyc")]
            for name in names:
                rel = os.path.relpath(os.path.join(base, name), context)
                with open(os.path.join(base, name), encoding="utf-8", errors="replace") as f:
                    files[rel.replace(os.sep, "/")] = f.readlines()
        with open(os.path.join(case.directory, "diff.patch"), encoding="utf-8") as f:
            patch_preimage(f.read(), case.id, files)
        if case.kind == "control":
            lines = files.get(case.bug_path)
            if lines is None:
                _bad(f"{case.id}: bug_location.path {case.bug_path!r} is not in context/")
            if case.bug_line > len(lines):
                _bad(f"{case.id}: bug_location.line {case.bug_line} is past the end of {case.bug_path}")
    return {"cases": len(cases), "traps": sum(c.kind == "trap" for c in cases.values()),
            "controls": sum(c.kind == "control" for c in cases.values()),
            "languages": dict(sorted(languages.items()))}


def normalize_path(path):
    path = str(path or "").strip().strip("`'\"").replace("\\", "/")
    changed = True
    while changed:
        changed = False
        for prefix in _PATH_PREFIX:
            if path.startswith(prefix):
                path = path[len(prefix):]
                changed = True
    return path


def _unwrap(line):
    line = line.strip()
    if line.startswith(("- ", "* ", "> ")):
        line = line[2:].strip()
    return line.strip("*_`").strip()


def extract_verdict(output):
    """The verdict on the last non-empty line, or none with a reason.

    A verdict followed by more prose is not accepted: the reviewer may have
    changed its mind. Markdown around the line and path prefixes are accepted.
    """
    if not output or not output.strip():
        return Verdict("none", reason="empty_output")
    lines = [line for line in output.splitlines() if line.strip()]
    while lines and not _unwrap(lines[-1]):  # a closing ``` fence, or an empty bullet
        lines.pop()
    if not lines:
        return Verdict("none", reason="empty_output")
    match = _VERDICT.match(_unwrap(lines[-1]))
    if not match:
        return Verdict("none", reason="no_verdict_line")
    body = match.group(1).strip().strip("*_`").strip()
    if body.casefold() == "clean":
        return Verdict("clean")
    bug = _BUG.match(body)
    if bug:
        return Verdict("bug", path=normalize_path(bug.group(1)), line=int(bug.group(2)))
    return Verdict("none", reason="garbled_verdict")


def grade(case, verdict):
    if verdict.kind == "none":
        return "no_verdict"
    if case.kind == "trap":
        return "clean_ok" if verdict.kind == "clean" else "false_alarm"
    if verdict.kind == "clean":
        return "miss_clean"
    if (verdict.path == normalize_path(case.bug_path)
            and verdict.line is not None
            and abs(verdict.line - case.bug_line) <= LOCATION_WINDOW):
        return "hit"
    return "miss_location"


def grade_records(cases, records):
    """Grade records (each with arm, case, run, output and optional usage)."""
    graded, seen = [], set()
    for record in records:
        key = (record.get("arm"), record.get("case"), record.get("run"))
        if key in seen:
            raise C.PBError("review-duplicate-record", f"duplicate record {key}")
        seen.add(key)
        case = cases.get(record.get("case"))
        if case is None:
            raise C.PBError("review-unknown-case", f"record names unknown case {record.get('case')!r}")
        verdict = extract_verdict(record.get("output"))
        graded.append({"arm": record["arm"], "case": case.id, "kind": case.kind,
                       "run": record["run"], "verdict": verdict.kind,
                       "reason": verdict.reason, "outcome": grade(case, verdict),
                       "vpath": verdict.path, "vline": verdict.line,
                       "usage": record.get("usage") or {}})
    return graded


def read_records(path):
    """Read a recorded-verdicts fixture."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise C.PBError("review-records-invalid", f"{path}: {e}")
    if not isinstance(data, dict) or data.get("schema") != RECORDS_SCHEMA:
        raise C.PBError("review-records-invalid", f"{path}: expected schema {RECORDS_SCHEMA}")
    records = data.get("records")
    if not isinstance(records, list):
        raise C.PBError("review-records-invalid", f"{path}: records must be a list")
    for i, r in enumerate(records):
        if (not isinstance(r, dict) or not isinstance(r.get("arm"), str)
                or not isinstance(r.get("case"), str) or type(r.get("run")) is not int
                or (r.get("output") is not None and not isinstance(r["output"], str))):
            raise C.PBError("review-records-invalid", f"{path}: record {i} is malformed")
    return records


def read_rows(path):
    """Read appended rows from a results dir (or one .jsonl file)."""
    if os.path.isfile(path):
        files = [path]
    else:
        one = os.path.join(path, "rows.jsonl")
        files = [one] if os.path.isfile(one) else []
        if not files:
            import glob
            files = sorted(glob.glob(os.path.join(path, "*.jsonl")))
    if not files:
        raise C.PBError("no-rows", f"no .jsonl rows in {path}")
    rows = []
    for fp in files:
        with open(fp) as f:
            lines = f.read().split("\n")
        last = max((i for i, line in enumerate(lines) if line.strip()), default=-1)
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as e:
                if n - 1 == last and not lines[last].rstrip().endswith("}"):
                    continue  # a run cut off mid-write leaves a torn last line; resume rewrites that row
                raise C.PBError("bad-row", f"{fp} line {n}: {e}")
    if not rows:
        raise C.PBError("no-rows", f"row files in {path} are empty")
    return rows


def grade_rows(rows, cases=None):
    """Re-grade live rows from their scrubbed output text (ignoring any stored outcome)."""
    cases = cases or load_corpus()
    # A failed run that was retried on resume leaves two rows for one (arm, case, rep): the later one counts.
    latest = {}
    for r in rows:
        latest[(r.get("arm"), r.get("task"), r.get("rep"))] = r
    rows = list(latest.values())
    return grade_records(cases, [{"arm": r.get("arm"), "case": r.get("task"),
                                  "run": r.get("rep"), "output": r.get("output"),
                                  "usage": r.get("usage") or {}} for r in rows])


def _flips(outcomes):
    ordered = [outcomes[k] for k in sorted(outcomes)]
    return sum(1 for a, b in zip(ordered, ordered[1:]) if a != b)


def summarize(graded, rates=None):
    """Per-arm rates, flip counts and usage. rates: a rate table for every arm, or {arm: table} per arm;
    an arm with no table gets cost None (compared in tokens)."""
    by_arm = defaultdict(list)
    for row in graded:
        by_arm[row["arm"]].append(row)
    out = {}
    for arm, rows in sorted(by_arm.items()):
        traps = [r for r in rows if r["kind"] == "trap"]
        controls = [r for r in rows if r["kind"] == "control"]
        per_case = defaultdict(dict)
        for r in rows:
            per_case[r["case"]][r["run"]] = r["outcome"]
        flips = {c: _flips(v) for c, v in sorted(per_case.items())}
        runs = {c: len(v) for c, v in sorted(per_case.items())}
        usage = {k: sum(int((r.get("usage") or {}).get(k) or 0) for r in rows)
                 for k in ("i", "cr", "cw", "o")}
        fa = sum(r["outcome"] == "false_alarm" for r in traps)
        hit = sum(r["outcome"] == "hit" for r in controls)
        # A run with no usable verdict is excluded from both rates (an arm that times out on traps must not look
        # careful) and reported on its own; the two-sided rule refuses to decide when it is not the same in both arms.
        judged_traps = [r for r in traps if r["outcome"] != "no_verdict"]
        judged_controls = [r for r in controls if r["outcome"] != "no_verdict"]
        out[arm] = {
            "trap_runs": len(traps), "false_alarms": fa,
            "false_alarm_rate": (fa / len(judged_traps)) if judged_traps else None,
            "control_runs": len(controls), "hits": hit,
            "hit_rate": (hit / len(judged_controls)) if judged_controls else None,
            "no_verdict": sum(r["outcome"] == "no_verdict" for r in rows),
            "no_verdict_traps": sum(r["outcome"] == "no_verdict" for r in traps),
            "no_verdict_controls": sum(r["outcome"] == "no_verdict" for r in controls),
            "miss_location": sum(r["outcome"] == "miss_location" for r in controls),
            "flips": flips, "flip_total": sum(flips.values()),
            "cases_with_flips": sum(v > 0 for v in flips.values()),
            "runs_per_case": runs, "min_runs_per_case": min(runs.values()) if runs else 0,
            "tokens": usage, "weighted_tokens": C.weighted(usage),
            "cost": _arm_cost(rows, _rates_for(rates, arm)),
            "rows": len(rows),
        }
    return out


def _rates_for(rates, arm):
    if not rates:
        return None
    if all(isinstance(v, dict) for v in rates.values()):
        return rates.get(arm)
    return rates


def _arm_cost(rows, rates):
    return sum(C.cost(r.get("usage") or {}, rates) for r in rows) if rates else None


def coverage_mismatch(a, b):
    """Why two arms cannot be compared, or None when they cover the same cases equally."""
    ar, br = a["runs_per_case"], b["runs_per_case"]
    only_a, only_b = sorted(set(ar) - set(br)), sorted(set(br) - set(ar))
    if only_a or only_b:
        parts = []
        if only_a:
            parts.append(f"cases only in arm A: {', '.join(only_a)}")
        if only_b:
            parts.append(f"cases only in arm B: {', '.join(only_b)}")
        return "; ".join(parts)
    uneven = [c for c in ar if ar[c] != br[c]]
    if uneven:
        first = sorted(uneven)[0]
        return f"run counts differ on {len(uneven)} cases ({first}: A {ar[first]}, B {br[first]})"
    return None


def compare_arms(a, b, name_a="A", name_b="B"):
    """Two-sided rule: fewer false alarms AND hit rate not lower, on matched rows."""
    mismatch = coverage_mismatch(a, b)
    if mismatch:
        return f"not comparable: {mismatch}"
    vals = (a["false_alarm_rate"], b["false_alarm_rate"], a["hit_rate"], b["hit_rate"])
    if any(v is None for v in vals):
        return "not decided: an arm has no trap runs or no control runs"
    prefix = f"noise (fewer than {MIN_RUNS} runs per case); " if min(
        a["min_runs_per_case"], b["min_runs_per_case"]) < MIN_RUNS else ""
    if (a["no_verdict_traps"], a["no_verdict_controls"]) != (b["no_verdict_traps"], b["no_verdict_controls"]):
        return (f"not decided: no-verdict runs differ ({name_a} {a['no_verdict']}, {name_b} {b['no_verdict']}); "
                "rerun or inspect them before comparing")
    fa_a, fa_b, hit_a, hit_b = vals
    for win, lose, fw, fl, hw, hl in ((name_a, name_b, fa_a, fa_b, hit_a, hit_b), (name_b, name_a, fa_b, fa_a, hit_b, hit_a)):
        if fw < fl and hw >= hl:
            return f"{prefix}{win} wins: fewer false alarms than {lose}, hit rate held"
    if fa_a != fa_b:
        fewer, other = (name_a, name_b) if fa_a < fa_b else (name_b, name_a)
        return f"{prefix}no win: {fewer} has fewer false alarms but hits fewer controls than {other}"
    if hit_a != hit_b:
        return f"{prefix}no win: same false-alarm rate, {name_a if hit_a > hit_b else name_b} hits more controls"
    return f"{prefix}no win: the arms tie"


def win_rule(summary):
    names = list(summary)
    if len(names) < 2:
        return "not decided: both arms are needed"
    if len(names) > 2:
        return "compare arms pairwise (summaries list every arm); the rule needs exactly two arms"
    return compare_arms(summary[names[0]], summary[names[1]], *names)


def _pct(n, d):
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "n/a"


def render(summary, md=False):
    lines = ["ParetoBench review bench, task set " + C.REVIEW_TASK_SET
             + f", {sum(s['rows'] for s in summary.values())} graded runs"
             + ("" if md else f", pb {__version__}"), ""]
    header = ["arm", "false-alarm rate (traps)", "hit rate (controls)", "no_verdict",
              "wrong location", "cases with flips", "flips", "weighted tokens"]
    if any(s["cost"] is not None for s in summary.values()):
        header.append("cost $")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join("---" for _ in header) + "|")
    for arm, s in summary.items():
        row = [arm, _pct(s["false_alarms"], s["trap_runs"] - s["no_verdict_traps"]),
               _pct(s["hits"], s["control_runs"] - s["no_verdict_controls"]),
               f"{s['no_verdict']} (traps {s['no_verdict_traps']}, controls {s['no_verdict_controls']})",
               str(s["miss_location"]), str(s["cases_with_flips"]), str(s["flip_total"]),
               f"{s['weighted_tokens']:,}"]
        if "cost $" in header:
            row.append("-" if s["cost"] is None else f"{s['cost']:.4f}")
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"Win rule: {win_rule(summary)}", ""]
    lines.append("Token totals and cost are cumulative over all graded runs; cost needs a model rate table.")
    return "\n".join(lines)


def per_case_table(graded):
    cells = defaultdict(lambda: defaultdict(dict))
    kinds = {}
    for r in graded:
        cells[r["case"]][r["arm"]][r["run"]] = r["outcome"]
        kinds[r["case"]] = r["kind"]
    arms = list(summarize(graded))
    lines = ["| case | kind | " + " | ".join(arms) + " |",
             "| --- | --- | " + " | ".join("---" for _ in arms) + " |"]
    for case in sorted(cells, key=lambda c: (kinds[c], c)):
        values = [", ".join(cells[case][a][k] for k in sorted(cells[case][a])) or "-"
                  for a in arms]
        lines.append(f"| {case} | {kinds[case]} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_reports(summary, out_dir):
    """Write summary.json and summary.md beside the rows."""
    jp = os.path.join(out_dir, "summary.json")
    mp = os.path.join(out_dir, "summary.md")
    with open(jp, "w") as f:
        json.dump(ST.clean({"bench": "review", "task_set": C.REVIEW_TASK_SET,
                            "pb_version": __version__, "arms": summary,
                            "win_rule": win_rule(summary)}), f, indent=2)
        f.write("\n")
    with open(mp, "w") as f:
        f.write(render(summary, md=True) + "\n")
    return jp, mp
