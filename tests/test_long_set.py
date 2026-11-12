import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest

from paretobench import config as C
from paretobench import runner as RUN
from paretobench import selftest_long as SL

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LONG = os.path.join(REPO, "tasks-long")
SHORT_HASH = "3c3185f48a7f97a0"  # the published short set: adding a second set must never move it


def load_gen():
    return SL.load_generator(LONG)


class TestTaskSetSelection(unittest.TestCase):
    def test_default_is_short_and_unchanged(self):
        self.assertEqual(C.tasks_dir(), os.path.join(REPO, "tasks"))
        self.assertEqual(C.tasks_dir("short"), os.path.join(REPO, "tasks"))
        self.assertEqual(C.task_set_hash(), SHORT_HASH)
        self.assertEqual(len(C.validate_tasks()), 20)

    def test_long_set_resolves_beside_the_short_set(self):
        self.assertEqual(C.tasks_dir("long-v1"), LONG)
        tasks = C.validate_tasks(LONG)
        self.assertEqual(list(tasks), SL.LONG_TASKS)
        self.assertNotEqual(C.task_set_hash(LONG), SHORT_HASH)
        self.assertEqual(C.task_set_hash(LONG), C.task_set_hash(LONG))

    def test_env_override_and_unknown_set(self):
        old = os.environ.get("PARETOBENCH_TASKS_LONG_V1")
        os.environ["PARETOBENCH_TASKS_LONG_V1"] = "/no/such/dir"
        try:
            with self.assertRaises(C.PBError) as cm:
                C.tasks_dir("long-v1")
            self.assertEqual(cm.exception.name, "tasks-dir-missing")
            self.assertIn("PARETOBENCH_TASKS_LONG_V1", str(cm.exception))
        finally:
            if old is None:
                del os.environ["PARETOBENCH_TASKS_LONG_V1"]
            else:
                os.environ["PARETOBENCH_TASKS_LONG_V1"] = old
        with self.assertRaises(C.PBError) as cm:
            C.tasks_dir("long-v9")
        self.assertEqual(cm.exception.name, "unknown-task-set")

    def test_budgets(self):
        self.assertEqual(C.task_budgets(LONG), {"default": 1800, "L6": 3600})
        self.assertEqual(C.task_budgets(os.path.join(REPO, "tasks")), {})
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "budgets.json"), "w") as f:
                f.write('{"default": "soon"}')
            with self.assertRaises(C.PBError) as cm:
                C.task_budgets(d)
            self.assertEqual(cm.exception.name, "budgets-file-invalid")

    def test_cli_has_the_option(self):
        from paretobench import cli
        with self.assertRaises(SystemExit):
            cli.main(["selftest", "--task-set", "nope"])


class TestGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = load_gen()

    def gen_to(self, task=None):
        d = tempfile.mkdtemp(prefix="pb-test-gen-")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        self.gen.prepare(d, task)
        return d

    def test_same_seed_is_byte_identical(self):
        for task in (None, "L2", "L6"):
            self.assertEqual(SL.tree_digest(self.gen_to(task)), SL.tree_digest(self.gen_to(task)), task)

    def test_task_setups_differ_from_the_base(self):
        base = SL.tree_digest(self.gen_to(None))
        digests = {t: SL.tree_digest(self.gen_to(t)) for t in ("L2", "L3", "L4", "L6", "L10", "L11")}
        self.assertEqual(len(set(digests.values()) | {base}), 7)

    def test_size_packages_and_large_files(self):
        d = self.gen_to(None)
        lines, pkgs, biggest = SL.repo_size(d)
        self.assertTrue(8000 <= lines <= 15000, lines)
        self.assertEqual(pkgs, ["api", "cli", "core", "ingest", "plugins", "store", "tests"])
        self.assertGreater(biggest, 1_500_000)
        self.assertGreater(os.path.getsize(os.path.join(self.gen_to("L6"), "data", "q3_ledger_report.txt")), 2_500_000)

    def test_base_suite_is_green_and_l2_has_exactly_one_failure(self):
        r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                           cwd=self.gen_to(None), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                           cwd=self.gen_to("L2"), capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_bulk_tier_applies_at_the_threshold", r.stderr)
        self.assertIn("failures=1", r.stderr)

    def test_l6_has_forty_files_with_the_deprecated_call(self):
        d = self.gen_to("L6")
        hits = 0
        for dp, _dns, fns in os.walk(d):
            for fn in fns:
                if fn.endswith(".py"):
                    with open(os.path.join(dp, fn)) as f:
                        hits += any(l.strip().startswith("repo.put_legacy(") for l in f)
        self.assertEqual(hits, 40)

    def test_unknown_task_is_refused(self):
        with self.assertRaises(ValueError):
            self.gen.prepare(tempfile.mkdtemp(), "L99")


class TestLongSelftest(unittest.TestCase):
    def test_every_reference_passes_every_untouched_fixture_fails(self):
        lines = []
        rc = SL.run("long-v1", out=lines.append)
        self.assertEqual(rc, 0, "\n".join(lines))
        self.assertEqual(len([l for l in lines if l.startswith("PASS L")]), 11)
        self.assertTrue(any(l.startswith("PASS fixture") for l in lines))

    def test_steps_are_calibrated(self):
        with open(os.path.join(LONG, "steps.json")) as f:
            doc = json.load(f)
        self.assertEqual(sorted(doc["steps"], key=lambda t: int(t[1:])), SL.LONG_TASKS)
        for task, n in doc["steps"].items():
            lo, hi = SL.step_range(doc, task)
            self.assertTrue(lo <= n <= hi, (task, n))
        self.assertGreater(doc["steps"]["L6"], 40)


def fake_long_adapter(script, mode):
    a = types.SimpleNamespace(name="pi", family="fake")
    a.validate = lambda m, ex: None
    a.version = lambda ex: "fake-1.0"
    a.setup_lane = lambda ex, m, work, slot, lane_name: {}
    a.build_command = lambda ex, m, prompt, lane, model_patch=None, extra_patches=(): (
        [sys.executable, script, mode, prompt], {})
    a.after_run = lambda lane: None

    def parse(rc, out, err, scrub):
        from paretobench.harnesses import RunFail
        if rc != 0:
            raise RunFail(f"fake exit {rc}: {err[-200:]}", out, err)
        return dict(i=5, cr=0, cw=0, o=2, reasoning=0, turns=3, tools=4), out.strip()
    a.parse = parse
    return a


FAKE_LONG = """\
import json, os, subprocess, sys
mode, prompt = sys.argv[1], sys.argv[2]
tasks = json.load(open(os.path.join(os.environ["FAKE_TASKS"], "tasks.json")))
task = next((t for t, p in tasks.items() if p == prompt), None)
if task is None or mode == "idle":
    print("ok")          # the warm-up request, or an agent that does nothing
    sys.exit(0)
subprocess.run([sys.executable, "-B", os.path.join(os.environ["FAKE_TASKS"], "reference", task + ".py")], check=True,
               capture_output=True)
print(open("ans.txt").read() if os.path.exists("ans.txt") else "done")
"""


class TestRunnerOnTheLongSet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.script = os.path.join(self.d, "fake_long.py")
        with open(self.script, "w") as f:
            f.write(FAKE_LONG)
        os.environ["FAKE_TASKS"] = LONG
        self.addCleanup(lambda: os.environ.pop("FAKE_TASKS", None))
        self.ex = {"pi_bin": "", "dsh_bin": "", "claude_bin": "", "steak_pi_package": "",
                   "steak_dsh_patch": "", "pi_agent_dir": self.d}
        self.models = {"fm": {"harnesses": ["pi"], "pi": ["--model", "x"],
                              "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0}}}

    def run_mode(self, mode, tasks, out):
        entries = RUN.build_entries("harness", self.models, self.ex, model="fm", harness_names=["pi"],
                                    registry={"pi": fake_long_adapter(self.script, mode)})
        RUN.run_bench("harness", entries, 1, 1, out, task_names=tasks, ex=self.ex, task_set="long-v1")
        with open(os.path.join(out, "rows.jsonl")) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_scripted_reference_agent_scores_and_idle_agent_does_not(self):
        rows = self.run_mode("reference", ["L9", "L4"], os.path.join(self.d, "ref"))
        self.assertEqual(sorted(r["task"] for r in rows), ["L4", "L9"])
        self.assertTrue(all(r["ok"] for r in rows), rows)
        self.assertTrue(all(r["task_set"] == C.task_set_hash(LONG) for r in rows))
        rows = self.run_mode("idle", ["L9", "L2"], os.path.join(self.d, "idle"))
        self.assertFalse(any(r["ok"] for r in rows))
        self.assertTrue(all(r["chk_err"] for r in rows))

    def test_runner_rejects_a_task_of_the_other_set(self):
        entries = RUN.build_entries("harness", self.models, self.ex, model="fm", harness_names=["pi"],
                                    registry={"pi": fake_long_adapter(self.script, "idle")})
        with self.assertRaises(C.PBError) as cm:
            RUN.run_bench("harness", entries, 1, 1, os.path.join(self.d, "x"), task_names=["t3"],
                          ex=self.ex, task_set="long-v1")
        self.assertEqual(cm.exception.name, "unknown-task")


class TestNeutrality(unittest.TestCase):
    """Files this work ships carry no model, provider or person names."""
    BANNED = re.compile(r"deepseek|qwen|haiku|sonnet|opus|anthropic|openai|gemini|mistral|openrouter|mercury|"
                        r"libertydesign|\bmike\b|berardi", re.I)

    def test_no_names_in_the_long_set_or_new_adapters(self):
        paths = []
        for dp, dns, fns in os.walk(LONG):
            dns[:] = [d for d in dns if d != "__pycache__"]
            paths += [os.path.join(dp, f) for f in fns if not f.endswith(".pyc")]
        paths += [os.path.join(REPO, "paretobench", p) for p in
                  ("selftest_long.py", "harnesses/steak_pi_lean.py", "harnesses/steak_dsh_long.py")]
        self.assertGreater(len(paths), 50)
        for p in paths:
            with open(p, errors="replace") as f:
                m = self.BANNED.search(f.read())
            self.assertIsNone(m, f"{p}: {m and m.group(0)}")


if __name__ == "__main__":
    unittest.main()
