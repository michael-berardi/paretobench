import json
import os
import tempfile
import unittest

from paretobench import config as C
from paretobench import report as R

MODELS = {
    "deepseek": {"harnesses": ["pi", "steak-pi", "dsh", "steak-dsh"],
                 "pi": ["--model", "x"], "rates": {"i": 1e-6, "cr": 1e-7, "cw": 0, "o": 1e-5}},
    "m2": {"harnesses": ["steak-pi"], "pi": ["--model", "y"],
           "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0}},
}


def legacy_row(arm, task, rep, ok=True, i=100, o=10, sec=5.0, model="deepseek"):
    return dict(arm=arm, model=model, task=task, rep=rep, ok=ok, sec=sec,
                i=i, cr=0, cw=0, o=o, reasoning=0, turns=2, tools=1,
                err="", chk_err="", retries=0, harness_version="0.2.2-rc.1", ts=1794421600)


class TestLegacyImport(unittest.TestCase):
    def test_arm_name_mapping(self):
        rows = R.normalize([legacy_row("sdsh", "t1", 0), legacy_row("dsh", "t1", 0),
                            legacy_row("sp", "t1", 0), legacy_row("cc", "t1", 0)])
        self.assertEqual([r["harness"] for r in rows],
                         ["steak-dsh", "dsh", "steak-pi", "claude-code"])
        self.assertTrue(all(r["bench"] == "harness" for r in rows))
        self.assertTrue(all(r["task_set"] == C.LEGACY_TASK_SET for r in rows))

    def test_summary_of_legacy_rows(self):
        rows = [legacy_row(a, t, 0, i=(100 if a == "sdsh" else 200))
                for a in ("sdsh", "dsh") for t in ("t1", "t2")]
        s = R.summarize(rows, MODELS)
        self.assertEqual(s["bench"], "harness")
        self.assertEqual(s["task_set"], C.LEGACY_TASK_SET)
        ms = s["groups"]["deepseek"]
        self.assertEqual(ms["baseline"], "dsh")
        self.assertIn("steak-dsh", ms["entries"])
        self.assertEqual(ms["vs_baseline"]["steak-dsh"]["verdict"], "better")

    def test_load_rows_from_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "deepseek.jsonl"), "w") as f:
                f.write(json.dumps(legacy_row("sdsh", "t1", 0)) + "\n")
                f.write(json.dumps(legacy_row("dsh", "t1", 0)) + "\n")
            rows, dir_path = R.load_rows(d)
            self.assertEqual(len(rows), 2)
            self.assertEqual(dir_path, d)

    def test_no_rows_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(C.PBError) as cm:
                R.load_rows(d)
            self.assertEqual(cm.exception.name, "no-rows")


class TestMixingRefused(unittest.TestCase):
    def test_two_task_sets(self):
        r1 = legacy_row("dsh", "t1", 0)
        r2 = legacy_row("dsh", "t2", 0)
        r1["task_set"] = "aaaa"
        r2["task_set"] = "bbbb"
        with self.assertRaises(C.PBError) as cm:
            R.summarize([r1, r2], MODELS)
        self.assertEqual(cm.exception.name, "mixed-task-sets")

    def test_legacy_plus_new(self):
        r1 = legacy_row("dsh", "t1", 0)  # no task_set -> legacy
        r2 = legacy_row("dsh", "t2", 0)
        r2["task_set"] = "aaaa"
        with self.assertRaises(C.PBError) as cm:
            R.summarize([r1, r2], MODELS)
        self.assertEqual(cm.exception.name, "mixed-task-sets")

    def test_one_legacy_set_accepted(self):
        rows = [legacy_row(a, t, 0) for a in ("sdsh", "dsh") for t in ("t1", "t2")]
        s = R.summarize(rows, MODELS)
        self.assertEqual(s["task_set"], C.LEGACY_TASK_SET)

    def test_mixed_benches(self):
        r1 = legacy_row("dsh", "t1", 0)
        r2 = legacy_row("dsh", "t1", 0)
        r2["bench"] = "model"
        with self.assertRaises(C.PBError) as cm:
            R.summarize([r1, r2], MODELS)
        self.assertEqual(cm.exception.name, "mixed-benches")

    def test_unknown_model(self):
        with self.assertRaises(C.PBError) as cm:
            R.summarize([legacy_row("dsh", "t1", 0, model="nope")], MODELS)
        self.assertEqual(cm.exception.name, "unknown-model")

    def test_unknown_baseline(self):
        with self.assertRaises(C.PBError) as cm:
            R.summarize([legacy_row("dsh", "t1", 0)], MODELS, baseline="nope")
        self.assertEqual(cm.exception.name, "unknown-baseline")


class TestModelBench(unittest.TestCase):
    def test_detects_model_bench(self):
        rows = []
        for m in ("deepseek", "m2"):
            r = legacy_row("sp", "t1", 0, model=m)
            r.update(bench="model", harness="steak-pi", task_set="aaaa", pb_version="0.1.0")
            rows.append(r)
        s = R.summarize(rows, MODELS)
        self.assertEqual(s["bench"], "model")
        # one harness across models: one group (the harness), entries are the models
        self.assertEqual(set(s["groups"]), {"steak-pi"})
        ms = s["groups"]["steak-pi"]
        self.assertEqual(list(ms["entries"]), ["deepseek", "m2"])
        self.assertIn("m2", ms["vs_baseline"])

    def test_frontier_flags_present(self):
        rows = [legacy_row(a, t, 0, i=(100 if a == "sdsh" else 200))
                for a in ("sdsh", "dsh") for t in ("t1", "t2")]
        s = R.summarize(rows, MODELS)
        ms = s["groups"]["deepseek"]
        self.assertTrue(ms["entries"]["steak-dsh"]["frontier_cost"])
        self.assertFalse(ms["entries"]["dsh"]["frontier_cost"])

    def test_summary_json_is_stable_and_clean(self):
        rows = [legacy_row(a, t, 0) for a in ("sdsh", "dsh") for t in ("t1", "t2")]
        s1 = R.summarize(rows, MODELS)
        s2 = R.summarize(rows, MODELS)
        self.assertEqual(json.dumps(R.ST.clean(s1), sort_keys=True),
                         json.dumps(R.ST.clean(s2), sort_keys=True))
        json.dumps(R.ST.clean(s1))  # no non-finite floats


if __name__ == "__main__":
    unittest.main()
