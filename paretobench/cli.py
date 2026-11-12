"""paretobench CLI: harness | model | report | selftest | doctor | validate."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from . import __version__
from . import config as C
from . import report as R
from . import runner as RUN
from . import harnesses as H


def _harness_cmd(args):
    models = C.load_models()
    ex = C.resolve_executables()
    names = [a.strip() for a in args.harnesses.split(",") if a.strip()]
    variants = {}
    for v in args.variant:
        if "=" not in v:
            raise C.PBError("bad-variant", f"--variant expects NAME=HARNESS:PATCH, got '{v}'")
        name, rest = v.split("=", 1)
        if ":" not in rest:
            raise C.PBError("bad-variant", f"--variant expects NAME=HARNESS:PATCH, got '{v}'")
        base, path = rest.split(":", 1)
        if name in H._MODULES or name in variants:
            raise C.PBError("bad-variant", f"variant name '{name}' collides with an existing harness")
        variants[name] = (base, os.path.abspath(os.path.expanduser(path)))
    tasks = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    entries = RUN.build_entries("harness", models, ex, model=args.model,
                                harness_names=names, variants=variants)
    RUN.run_bench("harness", entries, args.reps, args.par, args.out,
                  task_names=tasks, timeout=args.timeout, ex=ex, task_set=args.task_set)


def _model_cmd(args):
    models = C.load_models()
    ex = C.resolve_executables()
    keys = [a.strip() for a in args.models.split(",") if a.strip()]
    tasks = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    entries = RUN.build_entries("model", models, ex, harness=args.harness, model_keys=keys)
    RUN.run_bench("model", entries, args.reps, args.par, args.out,
                  task_names=tasks, timeout=args.timeout, ex=ex, task_set=args.task_set)


def _report_cmd(args):
    rows, dir_path = R.load_rows(args.dir)
    models = C.load_models()
    summary = R.summarize(rows, models, baseline=args.baseline)
    jp, mp = R.write_reports(summary, dir_path)
    if args.json:
        print(json.dumps(R.ST.clean(summary), indent=2))
    else:
        print(R.render(summary, md=args.md))
    print(f"wrote {jp} and {mp}")


def _selftest_cmd(args):
    if args.task_set and args.task_set != C.DEFAULT_TASK_SET:
        from . import selftest_long
        return selftest_long.run(args.task_set)
    td = C.tasks_dir()
    tasks = C.validate_tasks(td)
    expected = [f"t{i}" for i in range(1, 9)] + [f"h{i}" for i in range(1, 13)]
    if list(tasks) != expected:
        print(f"FAIL tasks.json: expected {expected}, got {list(tasks)}")
        return 1
    spec_dir = td
    import importlib.util
    spec = importlib.util.spec_from_file_location("pb_gen_fixture", os.path.join(td, "gen_fixture.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    check_py = os.path.join(td, "checks", "check.py")
    wrong_fix = {"h3", "h4"}

    def check(dest, task):
        r = subprocess.run([sys.executable, check_py, task, "ans.txt"],
                           cwd=dest, capture_output=True, text=True)
        return r.stdout.strip() == "true", r.stderr.strip()

    def run_script(dest, name):
        path = os.path.join(spec_dir, "reference", name + ".py")
        r = subprocess.run([sys.executable, path], cwd=dest, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"reference {name} failed: {r.stderr.strip()[-300:]}")

    def fresh():
        d = tempfile.mkdtemp(prefix="pb-selftest-")
        gen.prepare(d)
        with open(os.path.join(d, "ans.txt"), "w") as f:
            f.write("")
        return d

    failures = 0
    t0 = time.time()
    for task in tasks:
        problems = []
        d = fresh()
        try:
            ok, why = check(d, task)
            if ok:
                problems.append("check passes on untouched fixture")
            try:
                run_script(d, task)
                ok, why = check(d, task)
                if not ok:
                    problems.append(f"check fails after reference: {why}")
            except RuntimeError as e:
                problems.append(str(e))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        if task in wrong_fix:
            d = fresh()
            try:
                run_script(d, task + "_wrong")
                ok, _ = check(d, task)
                if ok:
                    problems.append("check passes after the obvious wrong fix")
            except RuntimeError as e:
                problems.append(str(e))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        if problems:
            failures += 1
            print(f"FAIL {task}: " + "; ".join(problems))
        else:
            print(f"PASS {task}")
    print(f"selftest: {len(tasks) - failures}/{len(tasks)} passed in {time.time() - t0:.1f}s",
          file=sys.stderr)
    return 1 if failures else 0


def _doctor_cmd(args):
    ex = C.resolve_executables()
    try:
        models = C.load_models()
    except C.PBError as e:
        print(f"models config: ERROR {e.name}: {e}")
        return 1
    print(f"paretobench {__version__}")
    print(f"models config: {C.models_path()} ({len(models)} models)")
    print(f"pi agent dir: {ex['pi_agent_dir']} "
          f"(auth.json {'present' if os.path.isfile(os.path.join(ex['pi_agent_dir'], 'auth.json')) else 'MISSING'})")
    if args.model:
        if args.model not in models:
            raise C.PBError("unknown-model", f"'{args.model}' not in models config (have: {', '.join(models)})")
        keys = [args.model]
    else:
        keys = sorted(models)
    missing = 0
    for name in C.HARNESS_NAMES:
        a = H.get_adapter(name)
        runnable = [k for k in keys if name in models[k].get("harnesses", [])]
        try:
            ver = a.version(ex)
            status = "ok"
        except Exception as e:
            ver = f"{getattr(e, 'name', 'version-failed')}: {e}"
            status = "MISSING"
            missing += 1
        print(f"{name:12} {status:7} {ver}")
        print(f"{'':12} runnable models: {', '.join(runnable) if runnable else '(none)'}")
    return 1 if missing else 0


def _validate_cmd(args):
    models = C.load_models()
    print(f"ok models config: {C.models_path()} ({len(models)} models: {', '.join(sorted(models))})")
    for ts in ([args.task_set] if args.task_set else list(C.TASK_SETS)):
        try:
            td = C.tasks_dir(ts)
        except C.PBError:
            if args.task_set:
                raise
            continue  # an install without the optional long set still validates
        tasks = C.validate_tasks(td)
        print(f"ok tasks [{ts}]: {td}/tasks.json ({len(tasks)} tasks), checks, fixture, generator, references")
        print(f"ok task set hash [{ts}]: {C.task_set_hash(td)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="paretobench",
                                 description="ParetoBench: one benchmark, two benches (harness and model).")
    ap.add_argument("--version", action="version", version=f"paretobench {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("harness", help="one model across harnesses")
    p.add_argument("--model", required=True)
    p.add_argument("--harnesses", default="pi,steak-pi,dsh,steak-dsh")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--par", type=int, default=2, help="parallel lanes per harness")
    p.add_argument("--out", required=True, help="results directory (rows.jsonl is appended)")
    p.add_argument("--tasks", help="comma-separated task ids (default: all)")
    p.add_argument("--timeout", type=int, default=None,
                   help="hard per-run timeout, seconds (default: the task set's budgets.json, else 600)")
    p.add_argument("--task-set", default=C.DEFAULT_TASK_SET, choices=sorted(C.TASK_SETS),
                   help="task set: short (default, 20 tasks) or long-v1 (11 long multi-step tasks)")
    p.add_argument("--variant", action="append", default=[], metavar="NAME=HARNESS:PATCH",
                   help="extra ablation arm: dsh-family harness plus this patch (repeatable)")
    p.set_defaults(fn=_harness_cmd)

    p = sub.add_parser("model", help="one harness across models")
    p.add_argument("--harness", default="steak-pi")
    p.add_argument("--models", required=True, help="comma-separated model keys")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--par", type=int, default=2)
    p.add_argument("--out", required=True)
    p.add_argument("--tasks")
    p.add_argument("--timeout", type=int, default=None)
    p.add_argument("--task-set", default=C.DEFAULT_TASK_SET, choices=sorted(C.TASK_SETS))
    p.set_defaults(fn=_model_cmd)

    p = sub.add_parser("report", help="summarize a results dir (both benches, legacy rows ok)")
    p.add_argument("dir")
    p.add_argument("--baseline", help="entry name to compare against")
    p.add_argument("--md", action="store_true", help="GitHub markdown tables")
    p.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    p.set_defaults(fn=_report_cmd)

    p = sub.add_parser("selftest", help="every task: check fails untouched, passes after reference")
    p.add_argument("--task-set", default=C.DEFAULT_TASK_SET, choices=sorted(C.TASK_SETS))
    p.set_defaults(fn=_selftest_cmd)

    p = sub.add_parser("doctor", help="harness executables, versions, runnable models; no model call")
    p.add_argument("--model", help="only this model key")
    p.set_defaults(fn=_doctor_cmd)

    p = sub.add_parser("validate", help="config and task files well formed")
    p.add_argument("--task-set", choices=sorted(C.TASK_SETS), help="only this task set (default: every one present)")
    p.set_defaults(fn=_validate_cmd)

    args = ap.parse_args(argv)
    try:
        C.load_env_file()
        rc = args.fn(args)
    except C.PBError as e:
        print(f"error: {e.name}: {e}", file=sys.stderr)
        return 2
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
