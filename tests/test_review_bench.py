"""Offline tests for the review bench: corpus, verdict grading, report math and a
scripted dry run. No test here calls a model."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

from paretobench import cli
from paretobench import config as C
from paretobench import harnesses as H
from paretobench import review as RV
from paretobench import review_runner as RR

FIXED_LOCK = "trap-lock-held-by-caller"
FIXED_LAZY = "trap-lazy-open-closed-by-exit"


def read(path):
    with open(path) as f:
        return f.read()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def records(*triples, arm="arm-a"):
    return [{"arm": arm, "case": case, "run": run, "output": output,
             "usage": {"i": 100, "cr": 0, "cw": 0, "o": 10}} for case, run, output in triples]


class TestCorpus(unittest.TestCase):
    def test_validate_shipped_corpus(self):
        counts = RV.validate_corpus()
        self.assertEqual((counts["cases"], counts["traps"], counts["controls"]), (33, 23, 10))
        cases = RV.load_corpus()
        self.assertEqual(len(cases), 33)
        self.assertEqual({c.language for c in cases.values()}, {"python", "javascript", "go"})

    def test_fixed_lock_case_is_truly_clean(self):
        case = RV.load_corpus()[FIXED_LOCK]
        text = read(os.path.join(case.directory, "context", "app", "metrics.py"))
        self.assertIn("self._counts.clear()\n            self._total = 0", text)
        patch = read(os.path.join(case.directory, "diff.patch"))
        self.assertIn("+            self._total = 0", patch)
        mod = load_module(os.path.join(case.directory, "context", "app", "metrics.py"), "pb_review_metrics")
        c = mod.Counter()
        c.record("a", 3)
        self.assertEqual(c.total(), 3)
        c.reset()
        self.assertEqual((c.total(), c.snapshot()), (0, {}))

    def test_fixed_lazy_case_cannot_reopen_after_close(self):
        case = RV.load_corpus()[FIXED_LAZY]
        text = read(os.path.join(case.directory, "context", "app", "export.py"))
        self.assertIn("self._closed = True", text)
        self.assertIn('raise ValueError("exporter is closed")', text)
        patch = read(os.path.join(case.directory, "diff.patch"))
        self.assertIn("+        self._closed = True", patch)
        from pathlib import Path
        mod = load_module(os.path.join(case.directory, "context", "app", "export.py"), "pb_review_export")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "export.csv"
            with mod.Exporter(path, ["id"]) as exporter:
                exporter.write(["1"])
            before = read(path)
            with self.assertRaises(ValueError):
                exporter.write(["2"])
            self.assertEqual(read(path), before)
            with mod.Exporter(os.path.join(d, "empty.csv"), ["id"]):
                pass
            self.assertFalse(os.path.exists(os.path.join(d, "empty.csv")))

    def test_validator_rejects_stale_patch_and_bad_bug_location(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "corpus")
            shutil.copytree(RV.corpus_dir(), root)
            case = os.path.join(root, FIXED_LOCK)
            patch = os.path.join(case, "diff.patch")
            original = read(patch)
            with open(patch, "w") as f:
                f.write(original.replace("@@ -19,10 +20,16 @@", "@@ -17,10 +18,16 @@"))
            with self.assertRaises(C.PBError) as bad:
                RV.validate_corpus(root)
            self.assertEqual(bad.exception.name, "review-corpus-invalid")
            with open(patch, "w") as f:
                f.write(original)
            meta = os.path.join(root, "control-aware-now-against-naive-column", "case.json")
            data = json.loads(read(meta))
            data["bug_location"]["line"] = 9999
            with open(meta, "w") as f:
                json.dump(data, f)
            with self.assertRaises(C.PBError):
                RV.validate_corpus(root)


class TestVerdict(unittest.TestCase):
    def test_extract_verdict(self):
        self.assertEqual(RV.extract_verdict("analysis\nVERDICT: clean").kind, "clean")
        self.assertEqual(RV.extract_verdict("analysis\n**VERDICT: clean**").kind, "clean")
        self.assertEqual(RV.extract_verdict("analysis\n```\nVERDICT: clean\n```").kind, "clean")
        self.assertEqual(RV.extract_verdict("analysis\n- VERDICT: clean").kind, "clean")
        v = RV.extract_verdict("analysis\nVERDICT: bug context/app/b.py:12")
        self.assertEqual((v.kind, v.path, v.line), ("bug", "app/b.py", 12))
        v = RV.extract_verdict("VERDICT: bug ./app/b.py:3")
        self.assertEqual((v.path, v.line), ("app/b.py", 3))
        self.assertEqual(RV.extract_verdict("VERDICT: maybe").reason, "garbled_verdict")
        self.assertEqual(RV.extract_verdict("VERDICT: clean\n\nBut wait, there is a bug.").reason,
                         "no_verdict_line")
        self.assertEqual(RV.extract_verdict("no verdict here").reason, "no_verdict_line")
        self.assertEqual(RV.extract_verdict("").reason, "empty_output")

    def test_grade_both_kinds(self):
        cases = RV.load_corpus()
        trap = cases[FIXED_LOCK]
        control = cases["control-aware-now-against-naive-column"]
        self.assertEqual(RV.grade(trap, RV.extract_verdict("VERDICT: clean")), "clean_ok")
        self.assertEqual(RV.grade(trap, RV.extract_verdict("VERDICT: bug app/metrics.py:32")),
                         "false_alarm")
        self.assertEqual(RV.grade(control, RV.extract_verdict("VERDICT: bug app/tokens.py:10")), "hit")
        self.assertEqual(RV.grade(control, RV.extract_verdict("VERDICT: bug app/tokens.py:99")),
                         "miss_location")
        self.assertEqual(RV.grade(control, RV.extract_verdict("VERDICT: bug other.py:7")), "miss_location")
        self.assertEqual(RV.grade(control, RV.extract_verdict("VERDICT: clean")), "miss_clean")
        self.assertEqual(RV.grade(trap, RV.extract_verdict("nothing")), "no_verdict")


class TestReport(unittest.TestCase):
    def test_summary_math_flips_and_cost(self):
        graded = RV.grade_records(RV.load_corpus(), records(
            (FIXED_LOCK, 0, "VERDICT: clean"), (FIXED_LOCK, 1, "VERDICT: bug app/metrics.py:32"),
            ("control-aware-now-against-naive-column", 0, "VERDICT: bug app/tokens.py:7"),
            ("control-aware-now-against-naive-column", 1, "VERDICT: clean")))
        s = RV.summarize(graded, {"i": 1e-6, "cr": 0, "cw": 0, "o": 1e-5})["arm-a"]
        self.assertEqual((s["trap_runs"], s["false_alarms"], s["false_alarm_rate"]), (2, 1, 0.5))
        self.assertEqual((s["control_runs"], s["hits"], s["hit_rate"]), (2, 1, 0.5))
        self.assertEqual((s["no_verdict"], s["miss_location"], s["flip_total"]), (0, 0, 2))
        self.assertEqual(s["cases_with_flips"], 2)
        self.assertEqual(s["tokens"], {"i": 400, "cr": 0, "cw": 0, "o": 40})
        self.assertAlmostEqual(s["cost"], 400 * 1e-6 + 40 * 1e-5)
        self.assertIn("weighted tokens", RV.render({"arm-a": s}))
        self.assertIn("false-alarm rate (traps)", RV.render({"arm-a": s}, md=True))

    def test_two_sided_win_rule_and_noise(self):
        def arm(fa, hit, runs=3, nvt=0, nvc=0):
            return {"false_alarm_rate": fa, "hit_rate": hit, "no_verdict": nvt + nvc,
                    "no_verdict_traps": nvt, "no_verdict_controls": nvc,
                    "runs_per_case": {"a": runs, "b": runs}, "min_runs_per_case": runs}
        self.assertIn("a wins", RV.win_rule({"a": arm(0.1, 0.9), "b": arm(0.4, 0.8)}))
        # the rule is two-sided: the second arm can win, and the line names it
        self.assertIn("b wins", RV.win_rule({"a": arm(0.4, 0.8), "b": arm(0.1, 0.9)}))
        self.assertIn("no win", RV.win_rule({"a": arm(0.1, 0.8), "b": arm(0.4, 0.9)}))
        self.assertIn("no win", RV.win_rule({"a": arm(0.4, 0.9), "b": arm(0.1, 0.8)}))
        self.assertIn("tie", RV.win_rule({"a": arm(0.2, 0.9), "b": arm(0.2, 0.9)}))
        self.assertIn("not decided: no-verdict", RV.win_rule({"a": arm(0.1, 0.9, nvt=2), "b": arm(0.4, 0.8)}))
        self.assertTrue(RV.win_rule({"a": arm(0.1, 0.9, 2), "b": arm(0.4, 0.8, 2)}).startswith("noise"))
        self.assertIn("not comparable", RV.win_rule({"a": arm(0.1, 0.9),
                                                     "b": arm(0.4, 0.8, runs=2)}))
        self.assertEqual(RV.win_rule({"a": arm(0.1, 0.9)}), "not decided: both arms are needed")

    def test_no_verdict_is_left_out_of_both_rates(self):
        graded = RV.grade_records(RV.load_corpus(), records(
            (FIXED_LOCK, 0, "VERDICT: clean"), (FIXED_LOCK, 1, ""), (FIXED_LOCK, 2, "VERDICT: bug app/metrics.py:32"),
            ("control-aware-now-against-naive-column", 0, "no verdict line")))
        s = RV.summarize(graded)["arm-a"]
        self.assertEqual((s["false_alarm_rate"], s["no_verdict_traps"]), (0.5, 1))
        self.assertIsNone(s["hit_rate"])  # its only control run had no verdict
        self.assertEqual(s["no_verdict_controls"], 1)

    def test_cost_uses_each_arms_own_rates(self):
        rows = records((FIXED_LOCK, 0, "VERDICT: clean"), arm="a") + records((FIXED_LOCK, 0, "VERDICT: clean"), arm="b")
        graded = RV.grade_records(RV.load_corpus(), rows)
        s = RV.summarize(graded, {"a": {"i": 1e-6, "cr": 0, "cw": 0, "o": 0}})
        self.assertAlmostEqual(s["a"]["cost"], 100 * 1e-6)
        self.assertIsNone(s["b"]["cost"])

    def test_torn_last_row_is_skipped_but_a_bad_middle_row_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rows.jsonl")
            with open(p, "w") as f:
                f.write('{"a": 1}\n{"a": 2}\n{"a": ')
            self.assertEqual(len(RV.read_rows(p)), 2)
            with open(p, "w") as f:
                f.write('{"a": 1}\nnot json\n{"a": 3}\n')
            with self.assertRaises(C.PBError):
                RV.read_rows(p)

    def test_shipped_fixture_dry_run(self):
        records = RV.read_records(RV.fixture_path())
        self.assertEqual(len(records), 48)
        graded = RV.grade_records(RV.load_corpus(), records)
        by_key = {(r["case"], r["arm"], r["run"]): r["outcome"] for r in graded}
        self.assertEqual(by_key[(FIXED_LOCK, "arm-a", 0)], "clean_ok")  # markdown-wrapped
        self.assertEqual(by_key[(FIXED_LOCK, "arm-b", 0)], "false_alarm")
        self.assertEqual(by_key[("trap-header-skip-pinned-by-test", "arm-b", 1)], "no_verdict")
        self.assertEqual(by_key[("control-page-slice-drops-last", "arm-b", 1)], "no_verdict")  # garbled
        self.assertEqual(by_key[("control-page-slice-drops-last", "arm-b", 2)], "no_verdict")  # not last
        self.assertEqual(by_key[("control-aware-now-against-naive-column", "arm-b", 0)], "hit")  # a/ prefix
        self.assertEqual(by_key[("control-sql-injection-search", "arm-a", 2)], "miss_location")
        self.assertEqual(by_key[("control-page-slice-drops-last", "arm-b", 0)], "hit")  # exact location
        summary = RV.summarize(graded)
        self.assertEqual((summary["arm-a"]["false_alarms"], summary["arm-b"]["false_alarms"]), (1, 9))
        self.assertEqual((summary["arm-a"]["hits"], summary["arm-b"]["hits"]), (11, 10))
        # arm-b has three no-verdict runs, so the rule declines to rank the arms on rates that exclude them
        self.assertIn("not decided: no-verdict runs differ", RV.render(summary))

    def test_cli_dry_run_and_validate(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["review", "--validate"]), 0)
            self.assertEqual(cli.main(["review", "--dry-run"]), 0)
            self.assertEqual(cli.main(["selftest", "--task-set", C.REVIEW_TASK_SET]), 0)
        text = out.getvalue()
        self.assertIn("33 cases", text)
        self.assertIn("48 recorded replies, no model called", text)
        self.assertIn("Win rule: not decided: no-verdict runs differ", text)


class TestReadOnlyCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.ex = {"pi_bin": "/fake/pi", "claude_bin": "/fake/claude", "pi_agent_dir": self.d,
                   "steak_pi_package": os.path.join(self.d, "steak-pi-package")}
        os.makedirs(self.ex["steak_pi_package"])
        for name, value in (("auth.json", {}), ("models.json", {})):
            with open(os.path.join(self.d, name), "w") as f:
                json.dump(value, f)
        with open(os.path.join(self.ex["steak_pi_package"], "package.json"), "w") as f:
            json.dump({"name": "steak-pi", "version": "9.9.9"}, f)
        self.mcfg = {"pi": ["--model", "example/model"], "claude": ["--model", "example/model"]}
        self.work = os.path.join(self.d, "work")
        os.makedirs(self.work)

    def test_pi_and_steak_pi_review_commands_are_read_only(self):
        for name in ("pi", "steak-pi"):
            adapter = H.get_adapter(name)
            lane = adapter.setup_lane(self.ex, self.mcfg, self.work, 0, name)
            argv, env = adapter.review_command(self.ex, self.mcfg, "Review the diff", lane)
            self.assertEqual(argv[-1], "Review the diff")
            self.assertIn("--tools", argv)
            self.assertIn("read,grep,find,ls", argv)
            for flag in ("--offline", "--no-skills", "--no-context-files", "--no-mcp"):
                self.assertIn(flag, argv)
            self.assertNotIn("bash", " ".join(argv))
            self.assertEqual(env["PI_CODING_AGENT_DIR"], lane["agent_dir"])

    def test_claude_code_review_command_has_no_write_tools(self):
        adapter = H.get_adapter("claude-code")
        argv, env = adapter.review_command(self.ex, self.mcfg, "Review the diff", {})
        self.assertEqual(argv[-1], "Review the diff")
        self.assertIn("Read,Glob,Grep", argv)
        self.assertNotIn("Write", argv)
        # --tools limits which tools exist (an allowlist alone only skips prompts), and plan mode is not used:
        # it pushes the model to emit a plan instead of a verdict line.
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep")
        self.assertNotIn("plan", argv)
        self.assertEqual(env, {})


FAKE_REVIEWER = textwrap.dedent("""\
    import json, os, sys
    with open(os.environ["PB_TEST_CWD_LOG"], "a") as f:
        f.write(os.getcwd() + "\\n")
    ev = {"type": "agent_end", "messages": [{"role": "assistant",
          "usage": {"input": 10, "output": 5},
          "content": [{"type": "text", "text": "Read the diff.\\nVERDICT: clean"}]}]}
    print(json.dumps(ev))
""")
SLOW_REVIEWER = "import time\ntime.sleep(30)\n"


def fake_adapter(script, slow=False):
    adapter = H.get_adapter("pi")  # reuse its event parser; only its command is replaced
    adapter = __import__("types").SimpleNamespace(
        name="pi", family="pi", validate=lambda m, ex: None,
        version=lambda ex: "fake-review-1", setup_lane=lambda ex, m, work, slot, name: {},
        review_command=lambda ex, m, prompt, lane: ([sys.executable, script, prompt], {}),
        parse=adapter.parse, after_run=lambda lane: None)
    if slow:
        adapter.review_command = lambda ex, m, prompt, lane: ([sys.executable, script], {})
    return adapter


class TestScriptedRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.log = os.path.join(self.d, "cwd.log")
        os.environ["PB_TEST_CWD_LOG"] = self.log
        self.addCleanup(lambda: os.environ.pop("PB_TEST_CWD_LOG", None))
        self.script = os.path.join(self.d, "reviewer.py")
        with open(self.script, "w") as f:
            f.write(FAKE_REVIEWER)
        self.models = {"fm": {"harnesses": ["pi"], "pi": ["--model", "x"],
                              "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0}}}
        self.out = os.path.join(self.d, "results")

    def test_rows_resume_and_random_workspace_names(self):
        cases = [FIXED_LOCK, FIXED_LAZY]
        RR.run(self.models, {}, "pi", "fm", None, 1, 2, self.out, case_ids=cases,
               registry={"pi": fake_adapter(self.script)}, verbose=False)
        rows = RV.read_rows(self.out)
        self.assertEqual(sorted(r["task"] for r in rows), sorted(cases))
        self.assertTrue(all(r["outcome"] == "clean_ok" for r in rows))
        self.assertTrue(all(r["usage"] == {"i": 10, "cr": 0, "cw": 0, "o": 5} for r in rows))
        workspaces = read(self.log).splitlines()
        self.assertEqual(len(workspaces), 2)
        self.assertEqual(len(set(workspaces)), 2)
        self.assertFalse(any(c in w for w in workspaces for c in cases))
        # resume: no new child, no new row
        RR.run(self.models, {}, "pi", "fm", None, 1, 2, self.out, case_ids=cases,
               registry={"pi": fake_adapter(self.script)}, verbose=False)
        self.assertEqual(len(read(self.log).splitlines()), 2)
        self.assertEqual(len(RV.read_rows(self.out)), 2)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "summary.md")))

    def test_bytecode_caches_never_reach_the_reviewer(self):
        case = RV.load_corpus()[FIXED_LOCK]
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as root:
            shutil.copytree(case.directory, os.path.join(src, "c"))
            cache = os.path.join(src, "c", "context", "app", "__pycache__")
            os.makedirs(cache, exist_ok=True)
            with open(os.path.join(cache, "metrics.cpython-311.pyc"), "wb") as f:
                f.write(FIXED_LOCK.encode())
            fake = __import__("types").SimpleNamespace(directory=os.path.join(src, "c"))
            ws = RR.stage(fake, root)
            found = [n for _b, _d, names in os.walk(ws) for n in names]
            self.assertFalse(any(n.endswith(".pyc") for n in found), found)
            self.assertEqual(sorted(os.listdir(ws)), ["context", "diff.patch"])

    def test_failed_rows_are_retried_and_a_changed_corpus_is_refused(self):
        slow = os.path.join(self.d, "slow.py")
        with open(slow, "w") as f:
            f.write(SLOW_REVIEWER)
        RR.run(self.models, {}, "pi", "fm", None, 1, 1, self.out, case_ids=[FIXED_LOCK],
               timeout=1, registry={"pi": fake_adapter(slow, slow=True)}, verbose=False)
        RR.run(self.models, {}, "pi", "fm", None, 1, 1, self.out, case_ids=[FIXED_LOCK],
               registry={"pi": fake_adapter(self.script)}, verbose=False)
        outcomes = [r["outcome"] for r in RV.read_rows(self.out)]
        self.assertEqual(outcomes, ["no_verdict", "clean_ok"])
        rows = os.path.join(self.out, "rows.jsonl")
        with open(rows) as f:
            first = json.loads(f.readline())
        first["task_set"] = "review-v1:0000000000000000"
        with open(rows, "a") as f:
            f.write(json.dumps(first) + "\n")
        with self.assertRaises(C.PBError) as cm:
            RR.run(self.models, {}, "pi", "fm", None, 1, 1, self.out, case_ids=[FIXED_LOCK],
                   registry={"pi": fake_adapter(self.script)}, verbose=False)
        self.assertEqual(cm.exception.name, "review-corpus-changed")

    def test_raw_log_and_row_are_scrubbed(self):
        secret = "sk-review-test-secret"
        auth_dir = os.path.join(self.d, "agent")
        os.makedirs(auth_dir)
        with open(os.path.join(auth_dir, "auth.json"), "w") as f:
            json.dump({"test": {"type": "api_key", "key": secret}}, f)
        script = os.path.join(self.d, "leaky.py")
        with open(script, "w") as f:
            f.write('import json, os\nprint(json.dumps({"type": "agent_end", "messages": '
                    '[{"role": "assistant", "usage": {}, "content": [{"type": "text", '
                    '"text": "key=" + os.environ["PB_TEST_SECRET"] + "\\nVERDICT: clean"}]}]}))\n')
        logs = os.path.join(self.d, "logs")
        os.environ["PB_TEST_SECRET"] = secret
        os.environ["PB_LOG_DIR"] = logs
        self.addCleanup(lambda: os.environ.pop("PB_TEST_SECRET", None))
        self.addCleanup(lambda: os.environ.pop("PB_LOG_DIR", None))
        RR.run(self.models, {"pi_agent_dir": auth_dir}, "pi", "fm", None, 1, 1, self.out,
               case_ids=[FIXED_LOCK], registry={"pi": fake_adapter(script)}, verbose=False)
        blob = read(os.path.join(logs, os.listdir(logs)[0])) + read(
            os.path.join(self.out, "rows.jsonl"))
        self.assertNotIn(secret, blob)
        self.assertIn("***", blob)

    def test_timeout_kills_the_child_and_keeps_the_row(self):
        slow = os.path.join(self.d, "slow.py")
        with open(slow, "w") as f:
            f.write(SLOW_REVIEWER)
        RR.run(self.models, {}, "pi", "fm", None, 1, 1, self.out, case_ids=[FIXED_LOCK],
               timeout=1, registry={"pi": fake_adapter(slow, slow=True)}, verbose=False)
        row = RV.read_rows(self.out)[0]
        self.assertEqual(row["outcome"], "no_verdict")
        self.assertIn("timeout after 1s", row["err"])


if __name__ == "__main__":
    unittest.main()
