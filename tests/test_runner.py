import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest

from paretobench import config as C
from paretobench import runner as RUN

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAKE_SCRIPT = """\
import sys
with open(sys.argv[1], "a") as f:
    f.write("call\\n")
print("ok")
"""

FAIL_SCRIPT = """\
import sys
sys.stderr.write("boom: fake harness cannot run\\n")
sys.exit(1)
"""

SLOW_SCRIPT = """\
import os, sys, time
with open(sys.argv[1], "w") as f:
    f.write(str(os.getpid()))
time.sleep(300)
"""

MODELS = {"fm": {"harnesses": ["pi", "steak-pi"], "pi": ["--model", "x"],
                 "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0}}}


def fake_adapter(script_path, count_file, fail=False):
    a = types.SimpleNamespace()
    a.name = "pi"
    a.family = "fake"
    a.validate = lambda m, ex: None
    a.version = lambda ex: "fake-1.0"
    a.setup_lane = lambda ex, m, work, slot, lane_name: {}
    a.build_command = lambda ex, m, prompt, lane, model_patch=None, extra_patches=(): (
        [sys.executable, script_path, count_file], {})
    a.after_run = lambda lane: None

    def parse(rc, out, err, scrub):
        if rc != 0:
            from paretobench.harnesses import RunFail
            raise RunFail(f"fake exit {rc}: {scrub(err)[-200:]}", out, err)
        return dict(i=1, cr=0, cw=0, o=1, reasoning=0, turns=1, tools=0), out.strip()

    a.parse = parse
    return a


class RunnerTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.count_file = os.path.join(self.d, "calls.txt")
        self.script = os.path.join(self.d, "fake_harness.py")
        with open(self.script, "w") as f:
            f.write(FAKE_SCRIPT)
        self.ex = {"pi_bin": "", "dsh_bin": "", "claude_bin": "", "steak_pi_package": "",
                   "steak_dsh_patch": "", "pi_agent_dir": self.d}
        self.out = os.path.join(self.d, "results")

    def calls(self):
        if not os.path.exists(self.count_file):
            return 0
        with open(self.count_file) as f:
            return len(f.read().splitlines())

    def run_fake(self, reps, harness_names=("pi",), registry_name="pi", adapter=None):
        adapter = adapter or fake_adapter(self.script, self.count_file)
        entries = RUN.build_entries("harness", MODELS, self.ex, model="fm",
                                    harness_names=list(harness_names),
                                    registry={registry_name: adapter})
        return RUN.run_bench("harness", entries, reps, 1, self.out,
                             task_names=["t3"], timeout=60, ex=self.ex)

    def rows(self):
        with open(os.path.join(self.out, "rows.jsonl")) as f:
            return [json.loads(l) for l in f if l.strip()]


class TestResume(RunnerTestBase):
    def test_existing_rows_skipped(self):
        os.makedirs(self.out)
        existing = dict(arm="pi", harness="pi", bench="harness", model="fm", task="t3", rep=0,
                        ok=True, sec=1.0, i=1, cr=0, cw=0, o=1, err="", chk_err="", retries=0,
                        harness_version="fake-1.0", ts=1)
        with open(os.path.join(self.out, "rows.jsonl"), "w") as f:
            f.write(json.dumps(existing) + "\n")
        self.run_fake(reps=2)
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(r["rep"] for r in rows), [0, 1])
        # one warm-up plus exactly one new run: rep 0 was not run again
        self.assertEqual(self.calls(), 2)
        r = rows[1]
        for field in ("bench", "harness", "model", "harness_version", "pb_version", "task_set"):
            self.assertIn(field, r)
        self.assertEqual(r["bench"], "harness")
        self.assertEqual(r["task_set"], C.task_set_hash())

    def test_nothing_to_do(self):
        os.makedirs(self.out)
        existing = dict(arm="pi", harness="pi", model="fm", task="t3", rep=0, ok=True, sec=1.0)
        with open(os.path.join(self.out, "rows.jsonl"), "w") as f:
            f.write(json.dumps(existing) + "\n")
        self.run_fake(reps=1)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.calls(), 0)  # no warm-up when there is nothing to do

    def test_legacy_arm_rows_resume(self):
        os.makedirs(self.out)
        existing = dict(arm="sp", model="fm", task="t3", rep=0, ok=True, sec=1.0)
        with open(os.path.join(self.out, "rows.jsonl"), "w") as f:
            f.write(json.dumps(existing) + "\n")
        self.run_fake(reps=1, harness_names=("steak-pi",), registry_name="steak-pi")
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.calls(), 0)


class TestModelBenchRows(RunnerTestBase):
    def test_row_carries_harness_not_model_key(self):
        adapter = fake_adapter(self.script, self.count_file)
        entries = RUN.build_entries("model", MODELS, self.ex, harness="steak-pi",
                                    model_keys=["fm"], registry={"steak-pi": adapter})
        RUN.run_bench("model", entries, 1, 1, self.out, task_names=["t3"], timeout=60, ex=self.ex)
        r = self.rows()[0]
        self.assertEqual(r["bench"], "model")
        self.assertEqual(r["arm"], "fm")
        self.assertEqual(r["harness"], "steak-pi")
        self.assertEqual(r["model"], "fm")
        self.assertNotIn("variant_of", r)
        # resume: the same row is skipped on a second call
        RUN.run_bench("model", entries, 1, 1, self.out, task_names=["t3"], timeout=60, ex=self.ex)
        self.assertEqual(len(self.rows()), 1)


class TestWarmupAbort(RunnerTestBase):
    def test_all_warmups_fail_aborts(self):
        script = os.path.join(self.d, "fail_harness.py")
        with open(script, "w") as f:
            f.write(FAIL_SCRIPT)
        adapter = fake_adapter(script, self.count_file)
        with self.assertRaises(C.PBError) as cm:
            self.run_fake(reps=1, adapter=adapter)
        self.assertEqual(cm.exception.name, "arm-cannot-run")
        self.assertFalse(os.path.exists(os.path.join(self.out, "rows.jsonl")))


class TestStopCleanup(unittest.TestCase):
    def test_sigterm_kills_child_and_removes_workdir(self):
        with tempfile.TemporaryDirectory() as d:
            tmpdir = os.path.join(d, "tmp")
            os.makedirs(tmpdir)
            pidfile = os.path.join(d, "child.pid")
            slow = os.path.join(d, "slow_harness.py")
            with open(slow, "w") as f:
                f.write(SLOW_SCRIPT)
            out = os.path.join(d, "results")
            runner_script = os.path.join(d, "run_fake.py")
            with open(runner_script, "w") as f:
                f.write(f"""\
import sys, types
sys.path.insert(0, {REPO!r})
from paretobench import runner as RUN
a = types.SimpleNamespace()
a.name = "pi"; a.family = "fake"
a.validate = lambda m, ex: None
a.version = lambda ex: "fake-1.0"
a.setup_lane = lambda ex, m, work, slot, lane_name: {{}}
a.build_command = lambda ex, m, prompt, lane, model_patch=None, extra_patches=(): (
    [sys.executable, {slow!r}, {pidfile!r}], {{}})
a.after_run = lambda lane: None
a.parse = lambda rc, out, err, scrub: ({{}}, "")
models = {MODELS!r}
ex = {{"pi_bin": "", "dsh_bin": "", "claude_bin": "", "steak_pi_package": "",
       "steak_dsh_patch": "", "pi_agent_dir": {d!r}}}
entries = RUN.build_entries("harness", models, ex, model="fm", harness_names=["pi"],
                            registry={{"pi": a}})
RUN.run_bench("harness", entries, 1, 1, {out!r}, task_names=["t3"], timeout=300, ex=ex)
""")
            env = {**os.environ, "TMPDIR": tmpdir}
            proc = subprocess.Popen([sys.executable, runner_script], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            child_pid = None
            try:
                deadline = time.time() + 60
                while time.time() < deadline:
                    if os.path.exists(pidfile):
                        with open(pidfile) as f:
                            txt = f.read().strip()
                        if txt:
                            child_pid = int(txt)
                            break
                    if proc.poll() is not None:
                        self.fail(f"runner exited early: {proc.stderr.read()[-500:]}")
                    time.sleep(0.2)
                self.assertIsNotNone(child_pid, "fake slow harness never started")
                os.kill(child_pid, 0)  # alive before the stop
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=30)
                self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
                # no child left
                deadline = time.time() + 10
                gone = False
                while time.time() < deadline:
                    try:
                        os.kill(child_pid, 0)
                        time.sleep(0.2)
                    except ProcessLookupError:
                        gone = True
                        break
                self.assertTrue(gone, f"child {child_pid} still alive after stop")
                # work dir removed
                base = os.path.join(tmpdir, "paretobench")
                self.assertTrue(not os.path.exists(base) or not os.listdir(base),
                                f"work dirs left behind: {os.listdir(base)}")
                # a stopped run wrote no result row
                rows_file = os.path.join(out, "rows.jsonl")
                self.assertTrue(not os.path.exists(rows_file) or os.path.getsize(rows_file) == 0)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
                proc.stdout.close()
                proc.stderr.close()
                if child_pid:
                    try:
                        os.killpg(child_pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass


if __name__ == "__main__":
    unittest.main()
