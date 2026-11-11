import copy
import json
import os
import tempfile
import unittest

from paretobench import config as C

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def good_models():
    with open(os.path.join(REPO, "configs", "models.example.json")) as f:
        return json.load(f)


class TestModelsValidation(unittest.TestCase):
    def test_example_is_valid(self):
        self.assertTrue(C.validate_models(good_models()))

    def test_real_config_if_present(self):
        p = C.models_path()
        if os.path.isfile(p):
            self.assertTrue(C.validate_models(C.load_models(p)))

    def test_missing_rates(self):
        m = good_models()
        del m["example-flat"]["rates"]
        with self.assertRaises(C.PBError) as cm:
            C.validate_models(m)
        self.assertEqual(cm.exception.name, "models-config-invalid")

    def test_unknown_harness(self):
        m = good_models()
        m["example-flat"]["harnesses"].append("nope")
        with self.assertRaises(C.PBError):
            C.validate_models(m)

    def test_duplicate_harness(self):
        m = good_models()
        m["example-flat"]["harnesses"].append("pi")
        with self.assertRaises(C.PBError):
            C.validate_models(m)

    def test_missing_pi_args(self):
        m = good_models()
        del m["example-flat"]["pi"]
        with self.assertRaises(C.PBError):
            C.validate_models(m)

    def test_dsh_without_key(self):
        m = good_models()
        del m["example-flat"]["key"]
        with self.assertRaises(C.PBError):
            C.validate_models(m)

    def test_empty(self):
        with self.assertRaises(C.PBError):
            C.validate_models({})

    def test_load_missing_file(self):
        with self.assertRaises(C.PBError) as cm:
            C.load_models("/nonexistent/paretobench-models.json")
        self.assertEqual(cm.exception.name, "models-config-missing")

    def test_load_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "models.json")
            with open(p, "w") as f:
                f.write("{not json")
            with self.assertRaises(C.PBError) as cm:
                C.load_models(p)
            self.assertEqual(cm.exception.name, "models-config-invalid")


class TestEnvFile(unittest.TestCase):
    def test_load_and_existing_wins(self):
        key = "PB_TEST_ENV_FILE_KEY"
        os.environ.pop(key, None)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "env")
            with open(p, "w") as f:
                f.write("# comment\n\n" + key + "=hello\n")
            C.load_env_file(p)
            self.assertEqual(os.environ.get(key), "hello")
            os.environ[key] = "keep"
            C.load_env_file(p)
            self.assertEqual(os.environ[key], "keep")
        os.environ.pop(key, None)

    def test_bad_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "env")
            with open(p, "w") as f:
                f.write("no-equals-sign\n")
            with self.assertRaises(C.PBError) as cm:
                C.load_env_file(p)
            self.assertEqual(cm.exception.name, "bad-env-file")

    def test_missing_file_is_ok(self):
        C.load_env_file("/nonexistent/paretobench-env")


class TestTaskSetHash(unittest.TestCase):
    def mini_tasks(self, d, prompt="do the thing"):
        os.makedirs(os.path.join(d, "checks"))
        os.makedirs(os.path.join(d, "fixture"))
        with open(os.path.join(d, "tasks.json"), "w") as f:
            json.dump({"x1": prompt}, f)
        with open(os.path.join(d, "gen_fixture.py"), "w") as f:
            f.write("def prepare(dest):\n    pass\n")
        with open(os.path.join(d, "checks", "check.py"), "w") as f:
            f.write("print('false')\n")
        with open(os.path.join(d, "fixture", "a.txt"), "w") as f:
            f.write("a\n")

    def test_stable_and_sensitive(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self.mini_tasks(d1)
            self.mini_tasks(d2)
            h1 = C.task_set_hash(d1)
            self.assertEqual(h1, C.task_set_hash(d1))
            self.assertEqual(h1, C.task_set_hash(d2))  # same content, different path
            with open(os.path.join(d2, "tasks.json"), "w") as f:
                json.dump({"x1": "changed prompt"}, f)
            self.assertNotEqual(h1, C.task_set_hash(d2))

    def test_real_task_set_hash(self):
        h = C.task_set_hash(os.path.join(REPO, "tasks"))
        self.assertEqual(len(h), 16)


class TestTasksValidation(unittest.TestCase):
    def test_real_tasks_valid(self):
        tasks = C.validate_tasks(os.path.join(REPO, "tasks"))
        self.assertEqual(len(tasks), 20)

    def test_missing_reference(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "checks"))
            os.makedirs(os.path.join(d, "fixture"))
            os.makedirs(os.path.join(d, "reference"))
            with open(os.path.join(d, "tasks.json"), "w") as f:
                json.dump({"x1": "prompt"}, f)
            for rel in ("gen_fixture.py", "checks/check.py"):
                with open(os.path.join(d, rel), "w") as f:
                    f.write("")
            with self.assertRaises(C.PBError) as cm:
                C.validate_tasks(d)
            self.assertEqual(cm.exception.name, "reference-missing")


class TestCostHelpers(unittest.TestCase):
    def test_metric_and_label(self):
        r = dict(i=100, cr=10, cw=10, o=10)
        free = {"i": 0, "cr": 0, "cw": 0, "o": 0}
        paid = {"i": 1e-6, "cr": 1e-7, "cw": 0, "o": 1e-5}
        self.assertEqual(C.metric_label(free), "weighted tokens")
        self.assertEqual(C.metric_label(paid), "cost $")
        self.assertAlmostEqual(C.metric(r, free), 100 + 1 + 12.5 + 40)
        self.assertAlmostEqual(C.metric(r, paid), 100e-6 + 10e-7 + 10e-5)
        self.assertEqual(C.total_input(r), 120)

    def test_yaml_emitter(self):
        y = C.to_yaml([{"id": "a", "config": {"x": {"y": [1, "two", True]}}}])
        self.assertIn("id: \"a\"", y)
        self.assertIn("y:", y)
        self.assertIn("- \"two\"", y)


if __name__ == "__main__":
    unittest.main()
