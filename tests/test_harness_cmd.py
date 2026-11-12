import json
import os
import tempfile
import unittest

from paretobench import config as C
from paretobench import harnesses as H

SECRET = "sk-TEST-SECRET-never-in-argv"
PROMPT = "do the task"


def make_ex(d):
    """Fake executables and a fake pi agent dir; nothing is executed here."""
    ex = {}
    for name, key in (("pi", "pi_bin"), ("dsh", "dsh_bin"), ("claude", "claude_bin")):
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(p, 0o755)
        ex[key] = p
    pkg = os.path.join(d, "steak-pi-package")
    os.makedirs(pkg)
    with open(os.path.join(pkg, "package.json"), "w") as f:
        json.dump({"version": "9.9.9"}, f)
    ex["steak_pi_package"] = pkg
    patch = os.path.join(d, "cordis.patch.yml")
    with open(patch, "w") as f:
        f.write("- id: x\n")
    ex["steak_dsh_patch"] = patch
    agent = os.path.join(d, "agent")
    os.makedirs(agent)
    with open(os.path.join(agent, "auth.json"), "w") as f:
        json.dump({"test": {"type": "api_key", "key": SECRET}}, f)
    with open(os.path.join(agent, "models.json"), "w") as f:
        json.dump({}, f)
    ex["pi_agent_dir"] = agent
    return ex


def mcfg():
    return {
        "harnesses": list(H._MODULES),
        "pi": ["--model", "gw/model", "--thinking", "medium"],
        "steak_pi_extra": ["--steak-pi-paid-route=gw/model"],
        "claude": ["--model", "claude-x", "--effort", "medium"],
        "key": {"auth": "test", "env": "TEST_API_KEY"},
        "dsh": {"provider": "gw", "model": "model", "route": {"baseURL": "https://x"}},
        "rates": {"i": 0, "cr": 0, "cw": 0, "o": 0},
    }


class TestCommandConstruction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ex = make_ex(self.tmp.name)
        self.m = mcfg()
        self.work = os.path.join(self.tmp.name, "work")
        os.makedirs(self.work)

    def lane(self, adapter, name):
        return adapter.setup_lane(self.ex, self.m, self.work, 0, name)

    def assert_no_secret(self, argv, env):
        self.assertNotIn(SECRET, argv)
        self.assertTrue(all(SECRET not in str(a) for a in argv))
        self.assertTrue(all(SECRET not in str(v) for v in env.values()))

    def test_pi(self):
        a = H.get_adapter("pi")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "pi")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane)
        self.assertEqual(argv, [self.ex["pi_bin"], "-p", "--mode", "json", "--no-session", "-ne",
                                "--model", "gw/model", "--thinking", "medium", PROMPT])
        self.assertEqual(env, {"PI_CODING_AGENT_DIR": lane["agent_dir"]})
        self.assert_no_secret(argv, env)
        with open(os.path.join(lane["agent_dir"], "settings.json")) as f:
            self.assertEqual(json.load(f), {"quietStartup": True, "packages": []})

    def test_steak_pi(self):
        a = H.get_adapter("steak-pi")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "steak-pi")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane)
        self.assertEqual(argv, [self.ex["pi_bin"], "-p", "--mode", "json", "--no-session",
                                "--model", "gw/model", "--thinking", "medium",
                                "--steak-pi-paid-route=gw/model", PROMPT])
        self.assertNotIn("-ne", argv)
        self.assert_no_secret(argv, env)
        with open(os.path.join(lane["agent_dir"], "settings.json")) as f:
            self.assertEqual(json.load(f), {"quietStartup": True, "packages": [self.ex["steak_pi_package"]]})
        # same raw binary and model args as stock pi, plus the declared steak-pi-only extras
        pi_argv, _ = H.get_adapter("pi").build_command(
            self.ex, self.m, PROMPT, self.lane(H.get_adapter("pi"), "pi"))
        self.assertEqual(argv[:5], pi_argv[:5])  # binary and -p --mode json --no-session
        self.assertEqual(argv[5:9], pi_argv[6:10])  # model args (pi has -ne at index 5)
        self.assertEqual(argv[9:-1], self.m["steak_pi_extra"])

    def test_dsh(self):
        a = H.get_adapter("dsh")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "dsh")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane, model_patch="/tmp/model.yml")
        self.assertEqual(argv, [self.ex["dsh_bin"], "headless", "--patch", "/tmp/model.yml",
                                "--json", "--permission-mode", "workspace-write",
                                "--approval-policy", "never", PROMPT])
        self.assertEqual(env["DSH_HOME"], lane["home"])
        self.assertEqual(env["DSH_TELEMETRY_MODE"], "DISABLED")
        self.assertNotIn("TEST_API_KEY", env)  # the runner adds the key, never the adapter
        self.assert_no_secret(argv, env)

    def test_steak_dsh(self):
        a = H.get_adapter("steak-dsh")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "steak-dsh")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane, model_patch="/tmp/model.yml",
                                    extra_patches=("/tmp/variant.yml",))
        self.assertEqual(argv, [self.ex["dsh_bin"], "headless",
                                "--patch", "/tmp/model.yml",
                                "--patch", self.ex["steak_dsh_patch"],
                                "--patch", "/tmp/variant.yml",
                                "--json", "--permission-mode", "workspace-write",
                                "--approval-policy", "never", PROMPT])
        self.assert_no_secret(argv, env)

    def test_steak_pi_lean(self):
        a = H.get_adapter("steak-pi-lean")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "steak-pi-lean")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane)
        base_argv, base_env = H.get_adapter("steak-pi").build_command(
            self.ex, self.m, PROMPT, self.lane(H.get_adapter("steak-pi"), "steak-pi"))
        self.assertEqual(argv[:-3], base_argv[:-1])  # identical to steak-pi up to the added flags
        self.assertEqual(argv[-3:], ["--exclude-tools", "ultraterm_subagents,todo", PROMPT])  # prompt last
        self.assertNotIn("-ne", argv)
        self.assertEqual(set(env), set(base_env))
        self.assert_no_secret(argv, env)
        with open(os.path.join(lane["agent_dir"], "settings.json")) as f:
            self.assertEqual(json.load(f), {"quietStartup": True, "packages": [self.ex["steak_pi_package"]]})
        self.assertTrue(a.version(self.ex).endswith(" lean"))

    def test_steak_dsh_long(self):
        a = H.get_adapter("steak-dsh-long")
        long_patch = os.path.join(os.path.dirname(self.ex["steak_dsh_patch"]), "long.patch.yml")
        with self.assertRaises(C.PBError) as cm:  # a bundle without long.patch.yml: named error
            a.validate(self.m, self.ex)
        self.assertEqual(cm.exception.name, "steak-dsh-long-patch-missing")
        self.assertIn("long.patch.yml", str(cm.exception))
        with open(long_patch, "w") as f:
            f.write("- id: y\n")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "steak-dsh-long")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane, model_patch="/tmp/model.yml",
                                    extra_patches=("/tmp/variant.yml",))
        self.assertEqual(argv, [self.ex["dsh_bin"], "headless",
                                "--patch", "/tmp/model.yml",
                                "--patch", self.ex["steak_dsh_patch"],
                                "--patch", long_patch,
                                "--patch", "/tmp/variant.yml",
                                "--json", "--permission-mode", "workspace-write",
                                "--approval-policy", "never", PROMPT])
        self.assertEqual(env["DSH_HOME"], lane["home"])
        self.assertNotIn("TEST_API_KEY", env)
        self.assert_no_secret(argv, env)

    def test_steak_dsh_long_needs_the_base_patch_first(self):
        ex = dict(self.ex, steak_dsh_patch="")
        with self.assertRaises(C.PBError) as cm:
            H.get_adapter("steak-dsh-long").validate(self.m, ex)
        self.assertEqual(cm.exception.name, "steak-dsh-patch-missing")

    def test_new_arms_registered_and_in_config_names(self):
        for n in ("steak-pi-lean", "steak-dsh-long"):
            self.assertIn(n, H._MODULES)
            self.assertIn(n, C.HARNESS_NAMES)
            self.assertEqual(H.get_adapter(n).name, n)
        self.assertEqual(H.get_adapter("steak-pi-lean").family, "pi")
        self.assertEqual(H.get_adapter("steak-dsh-long").family, "dsh")
        C.validate_models({"m": mcfg()})  # a model may list the new arms

    def test_claude_code(self):
        a = H.get_adapter("claude-code")
        a.validate(self.m, self.ex)
        lane = self.lane(a, "claude-code")
        argv, env = a.build_command(self.ex, self.m, PROMPT, lane)
        self.assertEqual(argv[:5], [self.ex["claude_bin"], "-p", "--model", "claude-x", "--effort"])
        self.assertEqual(argv[-1], PROMPT)
        for flag in ("--no-session-persistence", "--setting-sources", "--disable-slash-commands",
                     "--strict-mcp-config", "--permission-mode", "acceptEdits",
                     "--allowedTools", "Bash,Read,Edit,Write,Glob,Grep", "--output-format", "json"):
            self.assertIn(flag, argv)
        self.assert_no_secret(argv, env)

    def test_missing_binaries_named_errors(self):
        ex = dict(self.ex, pi_bin="", dsh_bin="", claude_bin="", steak_pi_package="", steak_dsh_patch="")
        for name, err in (("pi", "pi-bin-missing"), ("steak-pi", "pi-bin-missing"),
                          ("dsh", "dsh-bin-missing"), ("steak-dsh", "dsh-bin-missing"),
                          ("claude-code", "claude-bin-missing")):
            with self.assertRaises(C.PBError) as cm:
                H.get_adapter(name).validate(self.m, ex)
            self.assertEqual(cm.exception.name, err)

    def test_steak_specific_missing(self):
        ex = dict(self.ex, steak_pi_package="")
        with self.assertRaises(C.PBError) as cm:
            H.get_adapter("steak-pi").validate(self.m, ex)
        self.assertEqual(cm.exception.name, "steak-pi-package-missing")
        ex = dict(self.ex, steak_dsh_patch="")
        with self.assertRaises(C.PBError) as cm:
            H.get_adapter("steak-dsh").validate(self.m, ex)
        self.assertEqual(cm.exception.name, "steak-dsh-patch-missing")


class TestParsing(unittest.TestCase):
    def test_pi_parse(self):
        a = H.get_adapter("pi")
        end = {"type": "agent_end", "messages": [
            {"role": "user", "content": []},
            {"role": "assistant", "usage": {"input": 10, "cacheRead": 5, "cacheWrite": 2, "output": 7,
                                            "reasoning": 3},
             "content": [{"type": "text", "text": "ok"}, {"type": "toolCall"}]},
            {"role": "assistant", "usage": {"input": 1, "output": 1},
             "content": [{"type": "text", "text": "done"}]},
        ]}
        u, text = a.parse(0, json.dumps(end), "", lambda s: s)
        self.assertEqual((u["i"], u["cr"], u["cw"], u["o"], u["reasoning"], u["turns"], u["tools"]),
                         (11, 5, 2, 8, 3, 2, 1))
        self.assertEqual(text, "done")

    def test_pi_parse_failure(self):
        with self.assertRaises(H.RunFail):
            H.get_adapter("pi").parse(1, "", "boom", lambda s: s)

    def test_dsh_parse(self):
        ev = [
            {"type": "status", "phase": "step_start"},
            {"type": "status", "phase": "step_end",
             "usage": {"inputTokens": 10, "cacheReadTokens": 4, "cacheWriteTokens": 1,
                       "outputTokens": 6, "reasoningTokens": 2}},
            {"type": "tool_call"},
            {"type": "final", "reason": {"kind": "completed"}, "text": "answer"},
        ]
        out = "\n".join(json.dumps(e) for e in ev)
        u, text = H.get_adapter("dsh").parse(0, out, "", lambda s: s)
        self.assertEqual((u["i"], u["cr"], u["cw"], u["o"], u["turns"], u["tools"]), (10, 4, 1, 6, 1, 1))
        self.assertEqual(text, "answer")

    def test_dsh_parse_not_completed(self):
        out = json.dumps({"type": "final", "reason": {"kind": "aborted"}, "text": ""})
        with self.assertRaises(H.RunFail):
            H.get_adapter("steak-dsh").parse(0, out, "", lambda s: s)

    def test_claude_parse(self):
        j = {"usage": {"input_tokens": 9, "cache_read_input_tokens": 3,
                       "cache_creation_input_tokens": 2, "output_tokens": 4},
             "num_turns": 3, "result": "hi"}
        u, text = H.get_adapter("claude-code").parse(0, json.dumps(j), "", lambda s: s)
        self.assertEqual((u["i"], u["cr"], u["cw"], u["o"], u["turns"]), (9, 3, 2, 4, 3))
        self.assertEqual(text, "hi")
        with self.assertRaises(H.RunFail):
            H.get_adapter("claude-code").parse(0, "not json", "", lambda s: s)

    def test_scrub_applied_to_error(self):
        try:
            H.get_adapter("dsh").parse(1, "", SECRET + " leaked", lambda s: s.replace(SECRET, "***"))
            self.fail("expected RunFail")
        except H.RunFail as e:
            self.assertNotIn(SECRET, str(e))


if __name__ == "__main__":
    unittest.main()


class TestPiProviderError(unittest.TestCase):
    """Pi exits 0 when the provider refuses the request. That must be a named harness failure."""

    def test_error_stop_reason_is_a_run_failure(self):
        import json as _json
        from paretobench.harnesses import pi
        from paretobench.harnesses import RunFail
        out = _json.dumps({"type": "agent_end", "messages": [
            {"role": "user", "content": []},
            {"role": "assistant", "stopReason": "error", "errorMessage": "404: route is gone", "content": [], "usage": {}},
        ]})
        with self.assertRaises(RunFail) as ctx:
            pi.parse(0, out, "", lambda t: t)
        self.assertIn("pi provider error: 404: route is gone", str(ctx.exception))

    def test_no_assistant_message_is_a_run_failure(self):
        import json as _json
        from paretobench.harnesses import pi
        from paretobench.harnesses import RunFail
        out = _json.dumps({"type": "agent_end", "messages": [{"role": "user", "content": []}]})
        with self.assertRaises(RunFail):
            pi.parse(0, out, "", lambda t: t)
