"""Update contract tests. No network: the release API is an injected fetch or a loopback server."""
import hashlib
import http.server
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
from types import SimpleNamespace
from unittest import mock

from paretobench import __version__, cli, config as C, updates as U

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r"\x1b\[[0-9;]*m")
NOTICE = "paretobench 0.9.0 available"


def release(tag="v0.9.0", body="## 0.9.0\nFirst note.\n\n- Second note", prerelease=False, draft=False,
            base="https://example.test/"):
    return {"tag_name": tag, "prerelease": prerelease, "draft": draft, "body": body,
            "assets": [{"name": n, "browser_download_url": base + n} for n in (U.BUNDLE, U.SUMS)]}


def fake_fetch(record, seen=None):
    def fetch(url, headers, timeout):
        if seen is not None:
            seen.append({"url": url, "headers": headers, "timeout": timeout})
        if isinstance(record, BaseException):
            raise record
        return record
    return fetch


def no_fetch(url, headers, timeout):
    raise AssertionError("no request expected")


def args(**kw):
    base = dict(check=False, skip=False, auto=None, rollback=False, background=False, yes=False, cmd="update")
    base.update(kw)
    return SimpleNamespace(**base)


class TTY(io.StringIO):
    def isatty(self):
        return True


class Plain(io.StringIO):
    def isatty(self):
        return False


class Isolated(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="pb-update-test-")
        self.addCleanup(tmp.cleanup)
        self.d = tmp.name
        self.cache = os.path.join(self.d, "cache", "updates.json")
        self.settings = os.path.join(self.d, "config", "settings.json")
        # A clean environment: no CI, agent or opt-out variables leak in from the shell running the tests.
        self.env = {"HOME": self.d, "PATH": os.environ.get("PATH", ""),
                    "PARETOBENCH_UPDATE_CACHE": self.cache, "PARETOBENCH_SETTINGS": self.settings,
                    "PARETOBENCH_CONFIG": os.path.join(REPO, "configs", "models.example.json")}

    def seed(self, **values):
        cache = U.read_cache(self.cache)
        cache.update(checked_at=time.time(), latest_version="0.9.0", last_error="")
        cache.update(values)
        U.write_cache(cache, self.cache)

    def update(self, a, **kw):
        opts = dict(env=self.env, cache_file=self.cache, settings_file=self.settings,
                    stdin=Plain(), stdout=Plain(), stderr=Plain())
        opts.update(kw)
        rc = U.run_update(a, **opts)
        return rc, opts["stdout"].getvalue(), opts["stderr"].getvalue()

    def notice(self, kind="installer", **kw):
        err = TTY()
        shown = U.show_notice(stderr=err, path=self.cache, settings_file=self.settings, kind=kind, **kw)
        return shown, ANSI.sub("", err.getvalue()).splitlines()


class TestVersions(unittest.TestCase):
    def test_comparison(self):
        self.assertTrue(U.is_newer("0.8.1", "0.8.0"))
        self.assertTrue(U.is_newer("v1.0.0", "0.9.9"))
        self.assertTrue(U.is_newer("0.10.0", "0.9.0"))
        self.assertFalse(U.is_newer("0.8.0", "0.8.0"))
        self.assertFalse(U.is_newer("0.7.9", "0.8.0"))
        for garbage in ("garbage", "", None, "0.9", "0.9.0-rc.1", "0.9.0.1", "latest"):
            self.assertFalse(U.is_newer(garbage, "0.8.0"), garbage)

    def test_only_stable_releases_count(self):
        self.assertEqual(U.stable_version(release("v0.9.1")), "0.9.1")
        self.assertEqual(U.stable_version(release("v0.9.1", prerelease=True)), "")
        self.assertEqual(U.stable_version(release("v0.9.1", draft=True)), "")
        self.assertEqual(U.stable_version(release("0.9.1-nightly")), "")


class TestCheck(Isolated):
    def test_one_anonymous_get_per_day(self):
        seen = []
        cache, rel = U.check(fetch=fake_fetch(release(), seen), env=self.env, path=self.cache)
        self.assertEqual(cache["latest_version"], "0.9.0")
        self.assertIsNotNone(rel)
        U.check(fetch=fake_fetch(release(), seen), env=self.env, path=self.cache)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], {"url": U.RELEASE_API, "timeout": 4, "headers": {
            "User-Agent": "paretobench-update-check", "Accept": "application/vnd.github+json"}})
        self.seed(checked_at=time.time() - U.CHECK_INTERVAL - 1)
        U.check(fetch=fake_fetch(release(), seen), env=self.env, path=self.cache)
        self.assertEqual(len(seen), 2)

    def test_request_carries_no_identity(self):
        captured = {}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def urlopen(request, timeout):
            captured.update(url=request.full_url, headers=dict(request.header_items()),
                            data=request.data, method=request.get_method(), timeout=timeout)
            return Response(json.dumps(release()).encode())

        with mock.patch.object(U.urllib.request, "urlopen", urlopen):
            U.check(env=self.env, path=self.cache)
        self.assertEqual(captured["url"], "https://api.github.com/repos/" + U.REPO_SLUG + "/releases/latest")
        self.assertEqual(captured["method"], "GET")
        self.assertIsNone(captured["data"])
        self.assertEqual({k.lower() for k in captured["headers"]}, {"user-agent", "accept"})
        self.assertLessEqual(captured["timeout"], 4)

    def test_failure_recorded_with_cause_and_not_retried(self):
        seen = []
        for error, cause in ((urllib.error.HTTPError("u", 503, "x", {}, None), "HTTP 503"),
                             (urllib.error.URLError("no route"), "network error: no route"),
                             (TimeoutError(), "timed out after 4 s")):
            cache, rel = U.check(force=True, fetch=fake_fetch(error, seen), env=self.env, path=self.cache)
            self.assertIsNone(rel)
            self.assertEqual(U.read_cache(self.cache)["last_error"], cause)
        U.check(fetch=fake_fetch(release(), seen), env=self.env, path=self.cache)
        self.assertEqual(len(seen), 3)  # the failure counts as today's check

    def test_slot_is_claimed_before_the_request(self):
        def fetch(url, headers, timeout):
            claimed = U.read_cache(self.cache)
            self.assertGreater(claimed["checked_at"], 0)
            self.assertIn("did not finish", claimed["last_error"])
            raise KeyboardInterrupt  # the process dies mid-request
        with self.assertRaises(KeyboardInterrupt):
            U.check(fetch=fetch, env=self.env, path=self.cache)
        _, rel = U.check(fetch=no_fetch, env=self.env, path=self.cache)
        self.assertIsNone(rel)

    def test_failed_check_keeps_the_last_known_release(self):
        U.check(fetch=fake_fetch(release()), env=self.env, path=self.cache)
        U.check(force=True, fetch=fake_fetch(TimeoutError()), env=self.env, path=self.cache)
        self.assertEqual(U.read_cache(self.cache)["latest_version"], "0.9.0")

    def test_state_is_one_private_cache_file_and_one_settings_file(self):
        U.check(fetch=fake_fetch(release()), env=self.env, path=self.cache)
        self.notice()
        self.update(args(skip=True), fetch=no_fetch)
        self.update(args(auto="on"))
        self.update(args(auto="off"))
        self.assertEqual(os.listdir(os.path.dirname(self.cache)), ["updates.json"])
        self.assertEqual(os.listdir(os.path.dirname(self.settings)), ["settings.json"])
        for path in (self.cache, self.settings):
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertLess(os.path.getsize(self.cache), 1024)


class TestNotice(Isolated):
    def setUp(self):
        super().setUp()
        self.seed()

    def test_text_and_once_a_day_per_version(self):
        shown, lines = self.notice()
        self.assertTrue(shown)
        self.assertEqual(lines, [
            f"paretobench 0.9.0 available (you have {__version__}) · run: paretobench update",
            "turn on automatic updates: paretobench update --auto on · skip: paretobench update --skip"])
        self.assertEqual(self.notice(), (False, []))
        self.seed(notified_at=time.time() - U.CHECK_INTERVAL - 1)
        self.assertTrue(self.notice()[0])
        self.seed(latest_version="0.9.1")
        self.assertTrue(self.notice()[0])

    def test_skipped_version_is_quiet_until_a_newer_one(self):
        self.seed(skipped_version="0.9.0")
        self.assertEqual(self.notice(), (False, []))
        self.seed(latest_version="0.9.1")
        self.assertTrue(self.notice()[0])

    def test_not_newer_is_quiet(self):
        self.seed(latest_version=__version__)
        self.assertEqual(self.notice(), (False, []))

    def test_hint_names_the_right_command(self):
        spec = "git+https://github.com/" + U.REPO_SLUG + "@v0.9.0"
        self.assertEqual(U.upgrade_hint("uv", "0.9.0"), "uv tool install --force " + spec)
        self.assertEqual(U.upgrade_hint("pipx", "0.9.0"), "pipx install --force " + spec)
        self.assertEqual(U.upgrade_hint("pip", "0.9.0"), "paretobench update")
        self.assertEqual(U.manager_command("pip", "0.9.0"),
                         [sys.executable, "-m", "pip", "install", "--upgrade", spec])
        self.assertEqual(U.upgrade_hint("source", "0.9.0"), "git pull")
        self.assertEqual(U.upgrade_hint("installer", "0.9.0"), "paretobench update")
        # PyPI's "paretobench" is another project: no command may name the bare package.
        for kind in U.MANAGERS:
            self.assertFalse(U.manager_command(kind, "0.9.0")[-1] == "paretobench", kind)

    def test_silent_off_terminal_in_ci_agents_and_when_opted_out(self):
        s = U.read_settings(self.settings)
        allowed = lambda env, out=TTY(), err=TTY(), settings=s: U.notice_allowed(env, out, err, settings)
        self.assertTrue(allowed(self.env))
        self.assertFalse(allowed(self.env, out=Plain()))
        self.assertFalse(allowed(self.env, err=Plain()))
        self.assertFalse(allowed(dict(self.env, CI="true")))
        self.assertTrue(allowed(dict(self.env, CI="false")))
        self.assertFalse(allowed(dict(self.env, PARETOBENCH_NO_UPDATE_CHECK="1")))
        self.assertFalse(allowed(dict(self.env, CLAUDECODE="1")))
        self.assertFalse(allowed(dict(self.env, CODEX_SANDBOX="seatbelt")))
        self.assertFalse(allowed(self.env, settings=dict(s, check_automatically=False)))
        U.write_settings({"check_automatically": False}, self.settings)
        self.assertFalse(U.notice_allowed(self.env, TTY(), TTY()))


class TestCliPlacement(Isolated):
    def run_cli(self, argv, out=None, err=None, env=None):
        out, err = out or TTY(), err or TTY()
        get = mock.Mock(return_value=release())
        with mock.patch.dict(os.environ, env or self.env, clear=True), \
                mock.patch.object(U, "_get_json", get), \
                mock.patch.object(U, "detect_install_kind", return_value=("installer", self.d)), \
                mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            rc = cli.main(argv)
        return rc, out.getvalue(), ANSI.sub("", err.getvalue()), get.call_count

    def test_notice_goes_to_stderr_after_the_command(self):
        rc, out, err, calls = self.run_cli(["validate", "--task-set", "short"])
        self.assertEqual((rc, calls), (0, 1))
        self.assertIn("ok tasks [short]", out)
        self.assertNotIn("available", out)
        self.assertTrue(err.startswith(NOTICE), err)
        self.assertEqual(len(err.splitlines()), 2)

    def test_json_output_and_result_files_never_carry_it(self):
        rows = os.path.join(self.d, "rows")
        os.mkdir(rows)
        row = {"arm": "x", "task": "t1", "rep": 0, "ok": True, "sec": 1.0, "i": 1, "cr": 0, "cw": 0, "o": 1,
               "bench": "harness", "task_set": "short", "harness": "pi", "model": "example-flat"}
        with open(os.path.join(rows, "rows.jsonl"), "w") as f:
            f.write(json.dumps(row) + "\n")
        rc, out, err, calls = self.run_cli(["report", rows, "--json"])
        self.assertEqual((rc, calls), (0, 0))
        json.loads(out[:out.rindex("}") + 1])
        self.assertNotIn(NOTICE, out + err)
        rc, out, err, calls = self.run_cli(["report", rows])
        self.assertIn(NOTICE, err)
        self.assertNotIn(NOTICE, out)
        for name in os.listdir(rows):
            with open(os.path.join(rows, name), encoding="utf-8") as f:
                self.assertNotIn(NOTICE, f.read(), name)

    def test_redirected_ci_and_agent_runs_make_no_request(self):
        for env, out in ((self.env, Plain()), (dict(self.env, CI="1"), TTY()),
                         (dict(self.env, CLAUDECODE="1"), TTY())):
            rc, stdout, err, calls = self.run_cli(["validate", "--task-set", "short"], out=out, env=env)
            self.assertEqual((rc, calls, err), (0, 0, ""))
        self.assertFalse(os.path.exists(self.cache))

    def test_no_notice_after_a_failed_command(self):
        env = dict(self.env, PARETOBENCH_CONFIG=os.path.join(self.d, "missing.json"))
        rc, out, err, _ = self.run_cli(["validate"], env=env)
        self.assertEqual(rc, 2)
        self.assertNotIn(NOTICE, err)


class TestUpdateCommand(Isolated):
    def test_check_exit_codes(self):
        rc, out, _ = self.update(args(check=True), fetch=fake_fetch(release("v" + __version__)))
        self.assertEqual((rc, out), (0, f"paretobench {__version__} is current\n"))
        rc, out, _ = self.update(args(check=True), fetch=fake_fetch(release()))
        self.assertEqual((rc, out), (10, f"paretobench 0.9.0 available (you have {__version__})\n"))
        rc, _, err = self.update(args(check=True), fetch=fake_fetch(urllib.error.HTTPError("u", 404, "", {}, None)))
        self.assertEqual(rc, 1)
        self.assertIn("HTTP 404", err)

    def test_skip_uses_the_known_release(self):
        self.seed()
        rc, out, _ = self.update(args(skip=True), fetch=no_fetch)
        self.assertEqual((rc, U.read_cache(self.cache)["skipped_version"]), (0, "0.9.0"))
        self.assertIn("skipped 0.9.0", out)
        os.unlink(self.cache)
        rc, out, _ = self.update(args(skip=True), fetch=fake_fetch(release("v" + __version__)))
        self.assertEqual(rc, 0)
        self.assertIn("nothing to skip", out)

    def test_auto_is_off_by_default_and_persists(self):
        self.assertFalse(U.read_settings(self.settings)["auto_install"])
        _, out, _ = self.update(args(auto="status"))
        self.assertIn("install updates automatically: off", out)
        self.update(args(auto="on"))
        self.assertEqual(U.read_settings(self.settings),
                         {"check_automatically": True, "auto_install": True, "auto_asked": True})
        _, out, _ = self.update(args(auto="status"))
        self.assertIn("install updates automatically: on", out)
        self.assertIn(f"version {__version__}", out)
        log = U.log_path(self.env)
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "w") as f:
            f.write("old install\n")
        self.update(args(auto="off"))
        self.assertFalse(U.read_settings(self.settings)["auto_install"])
        self.assertFalse(os.path.exists(log))

    def test_tty_asks_to_install_then_once_about_auto(self):
        installs, questions = [], []

        def ask_with(answers):
            def ask():
                questions.append(None)
                return answers.pop(0)
            return ask
        kw = dict(fetch=fake_fetch(release()), install_kind=("installer", self.d),
                  installer=lambda *a: installs.append(a[2]), stdin=TTY(), stderr=TTY())
        rc, out, _ = self.update(args(), ask=ask_with(["", "n"]), **kw)
        self.assertEqual((rc, installs, len(questions)), (0, ["0.9.0"], 2))
        self.assertIn(f"paretobench {__version__} → 0.9.0\n  First note.\n  Second note\n", out)
        self.assertEqual(U.read_settings(self.settings)["auto_install"], False)
        self.update(args(), ask=ask_with([""]), **kw)  # never asked about auto again after "n"
        self.assertEqual(len(questions), 3)
        rc, out, _ = self.update(args(), ask=ask_with(["n"]), **kw)
        self.assertEqual((rc, len(installs)), (0, 2))
        self.assertIn("not installed", out)

    def test_without_a_terminal_it_installs_without_questions(self):
        installs = []
        rc, _, _ = self.update(args(), fetch=fake_fetch(release()), install_kind=("installer", self.d),
                               installer=lambda *a: installs.append(a[2]), ask=no_fetch)
        self.assertEqual((rc, installs), (0, ["0.9.0"]))
        self.assertFalse(U.read_settings(self.settings)["auto_asked"])

    def test_package_manager_install_runs_its_own_pinned_command(self):
        calls = []
        run = lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0, stdout="", stderr="")
        rc, out, _ = self.update(args(), fetch=fake_fetch(release()), install_kind=("uv", ""), runner=run,
                                 installer=no_fetch)
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [["uv", "tool", "install", "--force",
                                  "git+https://github.com/" + U.REPO_SLUG + "@v0.9.0"]])
        failing = lambda cmd, **kw: SimpleNamespace(returncode=2, stdout="", stderr="")
        rc, _, err = self.update(args(), fetch=fake_fetch(release()), install_kind=("pipx", ""), runner=failing)
        self.assertEqual(rc, 1)
        self.assertIn("upgrade-failed: pipx exited with 2", err)

    def test_source_checkout_is_left_alone(self):
        rc, _, err = self.update(args(), fetch=fake_fetch(release()), install_kind=("source", self.d),
                                 installer=no_fetch, runner=no_fetch)
        self.assertEqual(rc, 1)
        self.assertIn("git pull", err)


class TestAutoInstall(Isolated):
    def setUp(self):
        super().setUp()
        self.seed()
        U.write_settings({"auto_install": True}, self.settings)

    def test_auto_on_installs_instead_of_the_notice(self):
        spawn = mock.Mock()
        shown, lines = self.notice(spawn=spawn)
        self.assertEqual(shown, "auto")
        spawn.assert_called_once_with()
        self.assertEqual(lines, ["paretobench 0.9.0 is installing in the background; it applies on the next start."])
        self.assertEqual(self.notice(spawn=spawn), (False, []))
        self.assertEqual(spawn.call_count, 1)

    def test_spawn_is_detached_low_priority_and_its_log_bounded(self):
        log = U.log_path(self.env)
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "w") as f:
            f.write("x" * (300 * 1024))
        popen = mock.Mock()
        cmd = U.start_auto_install(env=self.env, popen=popen)
        self.assertEqual(cmd[-3:], ["paretobench.cli", "update", "--background"])
        kw = popen.call_args.kwargs
        self.assertTrue(kw.get("start_new_session") or kw.get("creationflags"))
        self.assertEqual(kw["stdin"], subprocess.DEVNULL)
        self.assertLessEqual(os.path.getsize(log), 256 * 1024)
        self.assertEqual(sorted(os.listdir(os.path.dirname(log))), ["auto-update.log", "updates.json"])

    def test_background_install_output_is_bounded(self):
        noisy = lambda cmd, **kw: SimpleNamespace(returncode=0, stdout="y" * (400 * 1024), stderr="")
        rc, out, _ = self.update(args(background=True), fetch=fake_fetch(release()),
                                 install_kind=("pip", ""), runner=noisy)
        self.assertEqual(rc, 0)
        self.assertLess(len(out), 256 * 1024)

    def test_failed_auto_install_records_the_cause_and_falls_back_to_the_notice(self):
        def broken(*a):
            raise C.PBError("checksum-mismatch", "SHA-256 mismatch")
        self.notice(spawn=mock.Mock())
        rc, _, err = self.update(args(background=True), fetch=fake_fetch(release()),
                                 install_kind=("installer", self.d), installer=broken, ask=no_fetch,
                                 stdin=TTY(), stderr=TTY())
        self.assertEqual(rc, 1)
        self.assertIn(f"{__version__} is unchanged", err)
        cache = U.read_cache(self.cache)
        self.assertEqual((cache["auto_failed_version"], cache["auto_error"]),
                         ("0.9.0", "checksum-mismatch: SHA-256 mismatch"))
        spawn = mock.Mock()
        shown, lines = self.notice(spawn=spawn)
        self.assertTrue(shown is True)
        spawn.assert_not_called()
        self.assertTrue(lines[0].startswith(NOTICE))
        _, _, err = self.update(args(check=True), fetch=fake_fetch(release()))
        self.assertIn("last automatic install failed: checksum-mismatch", err)
        self.seed(latest_version="0.9.1")
        self.assertEqual(self.notice(spawn=spawn)[0], "auto")

    def test_unexpected_errors_are_recorded_too(self):
        def broken(*a):
            raise OSError("disk full")
        rc, _, _ = self.update(args(background=True), fetch=fake_fetch(release()),
                               install_kind=("installer", self.d), installer=broken)
        self.assertEqual(rc, 1)
        self.assertEqual(U.read_cache(self.cache)["auto_error"], "disk full")
        rc, _, _ = self.update(args(background=True), fetch=fake_fetch(release()),
                               install_kind=("installer", self.d), installer=lambda *a: None)
        self.assertEqual((rc, U.read_cache(self.cache)["auto_error"]), (0, ""))


def make_bundle(folder, version, extra=None):
    src = os.path.join(folder, "src-" + version)
    os.makedirs(os.path.join(src, "paretobench"))
    os.makedirs(os.path.join(src, "tasks"))
    files = {"paretobench/__init__.py": f'__version__ = "{version}"\n',
             "paretobench/cli.py": 'from . import __version__\nprint(f"paretobench {__version__}")\n',
             "tasks/tasks.json": "{}"}
    for rel, text in files.items():
        with open(os.path.join(src, rel), "w") as f:
            f.write(text)
    archive = os.path.join(folder, f"bundle-{version}.tar.gz")
    with tarfile.open(archive, "w:gz") as t:
        for n in ("paretobench", "tasks"):
            t.add(os.path.join(src, n), arcname=n)
        if extra:
            t.add(os.path.join(src, "tasks", "tasks.json"), arcname=extra)
    with open(archive, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    sums = os.path.join(folder, f"SHA256SUMS-{version}")
    with open(sums, "w") as f:
        f.write(f"{sha}  paretobench.tar.gz\n{'1' * 64}  install.sh\n")
    return archive, sums


class TestInstallSafety(Isolated):
    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.d, "home")
        self.app = os.path.join(self.home, "app")
        os.makedirs(os.path.join(self.app, "paretobench"))
        with open(os.path.join(self.app, "paretobench", "__init__.py"), "w") as f:
            f.write('__version__ = "0.8.0"\n')

    def install(self, version="0.9.0", archive=None, sums=None):
        if archive is None:
            archive, sums = make_bundle(self.d, version)
        files = {"https://example.test/" + U.BUNDLE: archive, "https://example.test/" + U.SUMS: sums}

        def download(url, dest):
            with open(files[url], "rb") as src, open(dest, "wb") as out:
                out.write(src.read())
        return U.install_bundle(release("v" + version), self.app, version, download=download)

    def assert_untouched(self):
        self.assertEqual(U._bundle_version(self.app), "0.8.0")
        self.assertFalse(os.path.exists(self.app + ".previous"))
        self.assertEqual(sorted(os.listdir(self.home)), ["app"])  # staging folder removed

    def refused(self, name, **kw):
        with self.assertRaises(C.PBError) as cm:
            self.install(**kw)
        self.assertEqual(cm.exception.name, name)
        self.assert_untouched()

    def test_checksum_mismatch_refuses(self):
        archive, sums = make_bundle(self.d, "0.9.0")
        with open(sums, "w") as f:
            f.write("0" * 64 + "  paretobench.tar.gz\n")
        self.refused("checksum-mismatch", archive=archive, sums=sums)

    def test_missing_checksum_refuses(self):
        archive, sums = make_bundle(self.d, "0.9.0")
        with open(sums, "w") as f:
            f.write("0" * 64 + "  install.sh\n")
        self.refused("checksum-missing", archive=archive, sums=sums)

    def test_wrong_version_and_unsafe_archive_refuse(self):
        archive, sums = make_bundle(self.d, "0.9.1")
        self.refused("release-invalid", version="0.9.0", archive=archive, sums=sums)
        archive, sums = make_bundle(os.path.join(self.d), "0.9.2", extra="../escape.json")
        self.refused("unsafe-release-archive", version="0.9.2", archive=archive, sums=sums)
        self.assertFalse(os.path.exists(os.path.join(self.home, "escape.json")))

    def test_assets_only_over_https(self):
        dest = os.path.join(self.d, "x")
        for url in ("http://example.test/x", "file:///etc/hosts", "ftp://example.test/x"):
            with self.assertRaises(C.PBError) as cm:
                U._download(url, dest)
            self.assertEqual(cm.exception.name, "asset-url-invalid")

    def test_one_rollback_kept_and_restored(self):
        self.install("0.9.0")
        self.assertEqual((U._bundle_version(self.app), U._bundle_version(self.app + ".previous")),
                         ("0.9.0", "0.8.0"))
        self.install("0.9.1")
        self.assertEqual(U._bundle_version(self.app + ".previous"), "0.9.0")
        self.assertEqual(sorted(os.listdir(self.home)), ["app", "app.previous"])
        self.assertEqual(U.rollback_install(self.app), "0.9.0")
        self.assertEqual(sorted(os.listdir(self.home)), ["app"])
        with self.assertRaises(C.PBError) as cm:
            U.rollback_install(self.app)
        self.assertEqual(cm.exception.name, "no-rollback")

    def test_rollback_command_restores_the_previous_release(self):
        self.install("0.9.0")
        rc, out, _ = self.update(args(rollback=True), install_kind=("installer", self.app))
        self.assertEqual((rc, out), (0, "rolled back to paretobench 0.8.0\n"))
        rc, _, err = self.update(args(rollback=True), install_kind=("pip", ""))
        self.assertEqual(rc, 1)
        self.assertIn("pip install", err)

    def test_rollback_copy_removed_after_a_successful_run_or_seven_days(self):
        with open(os.path.join(self.app, "paretobench", "__init__.py"), "w") as f:
            f.write(f'__version__ = "{__version__}"\n')
        os.makedirs(os.path.join(self.app, "tasks"))
        with open(os.path.join(self.app, "tasks", "tasks.json"), "w") as f:
            f.write("{}")
        module = os.path.join(self.app, "paretobench", "updates.py")
        open(module, "w").close()
        previous = self.app + ".previous"
        os.mkdir(previous)
        self.assertFalse(U.prune_rollback(False, module_file=module))
        self.assertTrue(os.path.isdir(previous))
        self.assertTrue(U.prune_rollback(True, module_file=module))
        self.assertFalse(os.path.exists(previous))
        os.mkdir(previous)
        old = time.time() - U.PREVIOUS_MAX_AGE - 60
        os.utime(previous, (old, old))
        self.assertTrue(U.prune_rollback(False, module_file=module))
        self.assertFalse(os.path.exists(previous))
        os.mkdir(previous)  # a process still running the old version does not count as the new one running
        with open(os.path.join(self.app, "paretobench", "__init__.py"), "w") as f:
            f.write('__version__ = "99.0.0"\n')
        self.assertFalse(U.prune_rollback(True, module_file=module))

    def test_install_kinds(self):
        def touch(*parts):
            path = os.path.join(self.d, *parts)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
            return path
        site = ("lib", "python3.13", "site-packages", "paretobench", "updates.py")
        self.assertEqual(U.detect_install_kind(touch("uv", "tools", "paretobench", *site)), ("uv", ""))
        self.assertEqual(U.detect_install_kind(touch("pipx", "venvs", "paretobench", *site)), ("pipx", ""))
        self.assertEqual(U.detect_install_kind(touch("venv", *site)), ("pip", ""))
        bundle = touch("b", "app", "paretobench", "updates.py")
        touch("b", "app", "tasks", "tasks.json")
        self.assertEqual(U.detect_install_kind(bundle), ("installer", os.path.realpath(os.path.join(self.d, "b", "app"))))
        self.assertEqual(U.detect_install_kind(os.path.join(REPO, "paretobench", "updates.py"))[0], "source")


class TestLoopbackEndToEnd(Isolated):
    """The real CLI, HTTP client and installer against a loopback release server."""

    def test_check_and_install_over_http(self):
        folder = os.path.join(self.d, "web")
        os.mkdir(folder)
        archive, sums = make_bundle(self.d, "0.9.0")
        os.replace(archive, os.path.join(folder, U.BUNDLE))
        os.replace(sums, os.path.join(folder, U.SUMS))

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=folder, **kw)

            def log_message(self, *a):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}/"
        with open(os.path.join(folder, "latest.json"), "w") as f:
            json.dump(release(base=base), f)
        env = dict(self.env, PARETOBENCH_UPDATE_API=base + "latest.json")
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(sys, "stdout", Plain()), mock.patch.object(sys, "stderr", Plain()):
            self.assertEqual(cli.main(["update", "--check"]), 10)
        app = os.path.join(self.d, "home", "app")
        os.makedirs(app)
        rc, out, err = self.update(args(), env=env, install_kind=("installer", app))
        self.assertEqual(rc, 0, err)
        self.assertEqual(U._bundle_version(app), "0.9.0")
        self.assertEqual(sorted(os.listdir(os.path.dirname(app))), ["app", "app.previous"])


class TestNeutrality(unittest.TestCase):
    def test_update_files_add_no_identity(self):
        banned = re.compile(r"libertydesign|\bmike\b|berardi|/Users/|/home/\w|[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)
        for rel in ("paretobench/updates.py", "docs/updates.md", "PRIVACY.md"):
            with open(os.path.join(REPO, rel), encoding="utf-8") as f:
                text = f.read().replace(U.REPO_SLUG, "OWNER/REPO")
            self.assertIsNone(banned.search(text), rel)


if __name__ == "__main__":
    unittest.main()
