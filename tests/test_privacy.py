"""Privacy guards: no telemetry code or endpoints, offline commands stay offline,
child processes get telemetry off switches, and tool-owned files are private."""
import ast
import contextlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock

from paretobench import cli
from paretobench import config as C
from paretobench import harnesses as H
from paretobench import runner as RUN

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORBIDDEN_IMPORTS = {
    "sentry_sdk", "posthog", "segment", "mixpanel", "amplitude", "analytics",
    "bugsnag", "datadog", "opentelemetry", "torchtelemetry",
}
FORBIDDEN_HOSTS = (
    "sentry.io", "api.segment.io", "api.mixpanel.com", "api.amplitude.com",
    "api.posthog.com", "google-analytics.com", "googletagmanager.com",
    "stats.g.doubleclick.net", "fonts.googleapis.com", "fonts.gstatic.com",
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",
)
URL = re.compile(r"https?://[^\s\"'`)\]]+")
MODEL = {"fm": {"harnesses": ["pi"], "pi": ["--model", "m"],
                "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0}}}
SCRIPT = """\
import json, os
print(json.dumps({k: os.environ.get(k) for k in
    ('DO_NOT_TRACK', 'HF_HUB_DISABLE_TELEMETRY', 'DSH_TELEMETRY_MODE')}))
"""


def shipped_files():
    yield os.path.join(REPO, "README.md")
    for base in (os.path.join(REPO, "paretobench"), os.path.join(REPO, "scripts"),
                 os.path.join(REPO, "docs")):
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for n in names:
                if n.endswith((".py", ".sh", ".ps1", ".md")):
                    yield os.path.join(root, n)


class TestNoTelemetryCode(unittest.TestCase):
    def test_no_analytics_imports_or_endpoints_in_shipped_code(self):
        for path in shipped_files():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if path.endswith(".py"):
                for node in ast.walk(ast.parse(text)):
                    if isinstance(node, ast.Import):
                        names = [a.name.split(".")[0] for a in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.level == 0:
                        names = [(node.module or "").split(".")[0]]
                    else:
                        continue
                    for name in names:
                        self.assertNotIn(name, FORBIDDEN_IMPORTS, (path, name))
            for url in URL.findall(text):
                host = url.split("/", 3)[2].lower()
                for bad in FORBIDDEN_HOSTS:
                    self.assertFalse(host == bad or host.endswith("." + bad), (path, url))

    def test_off_switches_are_set_for_children_and_installers(self):
        self.assertEqual(C.TELEMETRY_OFF_ENV["DO_NOT_TRACK"], "1")
        self.assertEqual(C.TELEMETRY_OFF_ENV["HF_HUB_DISABLE_TELEMETRY"], "1")
        env = C.child_env({"DSH_TELEMETRY_MODE": "DISABLED", "DO_NOT_TRACK": "0"})
        self.assertEqual(env["DO_NOT_TRACK"], "1")  # our off switch wins over extras
        self.assertEqual(env["DSH_TELEMETRY_MODE"], "DISABLED")
        def read(rel):
            with open(os.path.join(REPO, rel), encoding="utf-8") as f:
                return f.read()
        sh = read("scripts/install.sh")
        ps1 = read("scripts/install.ps1")
        for name in ("DO_NOT_TRACK=1", "HF_HUB_DISABLE_TELEMETRY=1", "chmod 600 \"$MODELS\""):
            self.assertIn(name, sh)
        for name in ("DO_NOT_TRACK", "HF_HUB_DISABLE_TELEMETRY", "Set-PrivateAcl"):
            self.assertIn(name, ps1)
        dsh = read("paretobench/harnesses/dsh.py")
        self.assertIn('"DSH_TELEMETRY_MODE": "DISABLED"', dsh)

    def test_dsh_command_disables_its_telemetry(self):
        with tempfile.TemporaryDirectory() as d:
            ex = {"dsh_bin": os.path.join(d, "dsh")}
            open(ex["dsh_bin"], "w").close()
            mcfg = {"dsh": {"provider": "gw", "model": "m",
                            "route": {"baseURL": "https://example.test"}}}
            _argv, extra = H.get_adapter("dsh").build_command(
                ex, mcfg, "prompt", {"home": d}, model_patch=os.path.join(d, "model.yml"))
            env = C.child_env(extra)  # the runner merges adapter extras into the child env
            self.assertEqual(env["DSH_TELEMETRY_MODE"], "DISABLED")
            self.assertEqual(env["DO_NOT_TRACK"], "1")


class TestOfflineCommandsMakeNoNetworkCall(unittest.TestCase):
    def test_offline_cli_commands_never_open_a_socket(self):
        rows_dir = tempfile.mkdtemp(prefix="pb-privacy-rows-")
        self.addCleanup(shutil.rmtree, rows_dir, True)
        published = os.path.join(REPO, "benchmarks", "2026-11-14-harness-sonnet-short", "rows.jsonl")
        with open(published) as src:
            row = json.loads(src.readline())
        row["model"] = "example-flat"  # the shipped example config supplies its rates
        with open(os.path.join(rows_dir, "rows.jsonl"), "w") as dst:
            dst.write(json.dumps(row) + "\n")
        commands = [
            ["validate"], ["selftest"], ["report", rows_dir],
            ["review", "--validate"], ["review", "--dry-run"],
        ]
        sink = io.StringIO()
        with mock.patch("socket.socket", side_effect=AssertionError("network call attempted")), \
             mock.patch.object(C, "load_env_file", lambda *a, **k: None), \
             mock.patch.dict(os.environ, {"PARETOBENCH_CONFIG": os.path.join(REPO, "configs", "models.example.json")}), \
             contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            for cmd in commands:
                with self.subTest(cmd=cmd):
                    self.assertEqual(cli.main(cmd), 0, sink.getvalue()[-1000:])


class TestPrivateStorage(unittest.TestCase):
    def fake_run(self, out, log_dir=None, seen=None):
        env_file = os.path.join(os.path.dirname(out), "child-env.json")

        def parse(rc, out_text, err, scrub):
            if seen is not None:
                seen.append(json.loads(out_text.strip().splitlines()[0]))
            return {"i": 1, "cr": 0, "cw": 0, "o": 1}, ""

        a = types.SimpleNamespace(name="pi", family="fake")
        a.validate = lambda m, ex: None
        a.version = lambda ex: "fake"
        a.setup_lane = lambda ex, m, work, slot, lane_name: {}
        a.build_command = lambda ex, m, prompt, lane, model_patch=None, extra_patches=(): (
            [sys.executable, env_file], {})
        a.parse = parse
        a.after_run = lambda lane: None
        with open(env_file, "w") as f:
            f.write(SCRIPT)
        entries = RUN.build_entries("harness", MODEL, {}, model="fm", harness_names=["pi"],
                                    registry={"pi": a})
        env = {"PB_LOG_DIR": log_dir} if log_dir else {}
        with mock.patch.dict(os.environ, env, clear=False):
            RUN.run_bench("harness", entries, 1, 1, out, task_names=["t3"], timeout=30, ex={})

    def test_runner_children_get_telemetry_off_and_files_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "results")
            logs = os.path.join(d, "logs")
            seen = []
            self.fake_run(out, logs, seen)
            self.assertTrue(seen)
            for values in seen:
                self.assertEqual(values["DO_NOT_TRACK"], "1")
                self.assertEqual(values["HF_HUB_DISABLE_TELEMETRY"], "1")
            mode = lambda p: stat.S_IMODE(os.stat(p).st_mode)
            self.assertEqual(mode(out), 0o700)
            self.assertEqual(mode(logs), 0o700)
            self.assertEqual(mode(os.path.join(out, "rows.jsonl")), 0o600)
            for name in os.listdir(logs):
                self.assertEqual(mode(os.path.join(logs, name)), 0o600)

    def test_log_retention_bound(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                with open(os.path.join(d, f"run-{i}.jsonl"), "w") as f:
                    f.write("x")
            with mock.patch.dict(os.environ, {"PB_LOG_KEEP": "2"}):
                C.prune_logs(d)
            self.assertEqual(len(os.listdir(d)), 2)
            with mock.patch.dict(os.environ, {"PB_LOG_KEEP": "0"}):
                with self.assertRaises(C.PBError) as bad:
                    C.log_keep()
            self.assertEqual(bad.exception.name, "bad-log-keep")


if __name__ == "__main__":
    unittest.main()
