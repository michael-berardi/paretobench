"""Selftest for a long task set (long-v1): every task's hidden checker fails on the untouched
fixture and passes after its scripted reference solution; where a task has an obvious wrong solution
(reference/<task>_wrong.py) the checker must fail it too; each reference's tool-step count is inside
the calibrated range and equals the count recorded in steps.json; two generations with the same seed
are byte-identical; the repository has the promised size and package count."""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from . import config as C

LONG_TASKS = [f"L{i}" for i in range(1, 12)]


def load_generator(td):
    spec = importlib.util.spec_from_file_location("pb_gen_fixture_long", os.path.join(td, "gen_fixture.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    return gen


def tree_digest(root):
    """One sha256 over every path and content below root (sorted, __pycache__ ignored)."""
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d != "__pycache__")
        for fn in sorted(fns):
            if fn.endswith(".pyc"):
                continue
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                h.update(os.path.relpath(p, root).encode() + b"\0" + f.read() + b"\0")
    return h.hexdigest()


def repo_size(root):
    """(python lines, top-level packages incl. tests, bytes of the largest file)."""
    lines, pkgs, biggest = 0, [], 0
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d != "__pycache__")
        for fn in fns:
            p = os.path.join(dp, fn)
            biggest = max(biggest, os.path.getsize(p))
            if fn.endswith(".py"):
                with open(p, errors="replace") as f:
                    lines += sum(1 for _ in f)
    for n in sorted(os.listdir(root)):
        if os.path.isfile(os.path.join(root, n, "__init__.py")):
            pkgs.append(n)
    return lines, pkgs, biggest


def step_range(steps_doc, task):
    r = steps_doc.get("range", {})
    lo, hi = r.get(task) or r.get("default") or [10, 40]
    return lo, hi


def run(task_set="long-v1", out=print):
    td = C.tasks_dir(task_set)
    tasks = C.validate_tasks(td)
    if list(tasks) != LONG_TASKS:
        out(f"FAIL tasks.json: expected {LONG_TASKS}, got {list(tasks)}")
        return 1
    gen = load_generator(td)
    check_py = os.path.join(td, "checks", "check.py")
    with open(os.path.join(td, "steps.json")) as f:
        steps_doc = json.load(f)
    recorded = steps_doc["steps"]

    def fresh(task):
        d = tempfile.mkdtemp(prefix="pb-selftest-long-")
        gen.prepare(d, task)
        with open(os.path.join(d, "ans.txt"), "w") as f:
            f.write("")
        return d

    def check(d, task):
        r = subprocess.run([sys.executable, check_py, task, "ans.txt"], cwd=d, capture_output=True,
                           text=True, timeout=900)
        return r.stdout.strip() == "true", r.stderr.strip()

    def run_ref(d, name):
        path = os.path.join(td, "reference", name + ".py")
        r = subprocess.run([sys.executable, "-B", path], cwd=d, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise RuntimeError(f"reference {name} failed: {(r.stdout + r.stderr).strip()[-400:]}")
        m = re.search(r"STEPS=(\d+)", r.stderr)
        return int(m.group(1)) if m else None

    failures, t0 = 0, time.time()
    for task in LONG_TASKS:
        problems, steps = [], None
        d = fresh(task)
        try:
            ok, _ = check(d, task)
            if ok:
                problems.append("check passes on the untouched fixture")
            try:
                steps = run_ref(d, task)
                ok, why = check(d, task)
                if not ok:
                    problems.append(f"check fails after the reference: {why[:300]}")
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                problems.append(str(e))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        lo, hi = step_range(steps_doc, task)
        if steps is None:
            problems.append("reference reports no step count")
        else:
            if not lo <= steps <= hi:
                problems.append(f"reference has {steps} tool steps, outside the calibrated range {lo}-{hi}")
            if recorded.get(task) != steps:
                problems.append(f"steps.json records {recorded.get(task)}, the reference has {steps}")
        if os.path.isfile(os.path.join(td, "reference", task + "_wrong.py")):
            d = fresh(task)
            try:
                run_ref(d, task + "_wrong")
                ok, _ = check(d, task)
                if ok:
                    problems.append("check passes after the obvious wrong solution")
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                problems.append(str(e))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        if problems:
            failures += 1
            out(f"FAIL {task}: " + "; ".join(problems))
        else:
            out(f"PASS {task} ({steps} steps)")

    problems = []
    for task in [None] + LONG_TASKS:
        a, b = tempfile.mkdtemp(prefix="pb-det-a-"), tempfile.mkdtemp(prefix="pb-det-b-")
        try:
            gen.prepare(a, task)
            gen.prepare(b, task)
            if tree_digest(a) != tree_digest(b):
                problems.append(f"two generations of {task or 'the base'} differ")
            if task is None:
                lines, pkgs, biggest = repo_size(a)
                if not 8000 <= lines <= 15000:
                    problems.append(f"{lines} Python lines, expected 8000 to 15000")
                if not 5 <= len(pkgs) <= 7:
                    problems.append(f"{len(pkgs)} packages ({', '.join(pkgs)}), expected 5 to 7")
                if biggest < 1_500_000:
                    problems.append(f"largest generated file is {biggest} bytes, expected a large log or data file")
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)
    if problems:
        failures += 1
        out("FAIL fixture: " + "; ".join(problems))
    else:
        out("PASS fixture (deterministic for the base and every task; size and package count in range)")
    out(f"selftest [{task_set}]: {len(LONG_TASKS) + 1 - failures}/{len(LONG_TASKS) + 1} passed in "
        f"{time.time() - t0:.1f}s")
    return 1 if failures else 0
