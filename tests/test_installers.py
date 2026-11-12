"""Installer tests: static guards for Windows-only code, and install.sh run against a local file:// release."""
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS1 = open(os.path.join(REPO, "scripts", "install.ps1"), encoding="utf-8").read()
SH = os.path.join(REPO, "scripts", "install.sh")


class TestInstallPs1Static(unittest.TestCase):
    def test_cmd_shim_not_written_ascii(self):
        # Set-Content -Encoding Ascii turns a non-ASCII profile path into '?'.
        for line in PS1.splitlines():
            if ".cmd" in line and "Set-Content" in line:
                self.fail("a .cmd shim is written with Set-Content: " + line)
        self.assertNotRegex(PS1, r"Set-Content[^\n]*\$cmd")
        self.assertIn("OEMCodePage", PS1)

    def test_default_shim_is_relative_and_isolated(self):
        self.assertIn(r"%~dp0..\app", PS1)
        self.assertIn(r"%~dp0..\app\tasks", PS1)
        self.assertIn("'setlocal'", PS1)

    def test_no_move_item_from_temp(self):
        self.assertNotRegex(PS1, r"Move-Item \$src")
        self.assertNotIn("'src'", PS1)

    def test_raw_user_path_read(self):
        self.assertIn("DoNotExpandEnvironmentNames", PS1)
        self.assertNotIn("GetEnvironmentVariable('Path', 'User')", PS1)

    def test_system_tar_and_cleanup(self):
        self.assertIn(r"System32\tar.exe", PS1)
        self.assertIn("if ($stage) { Remove-Item", PS1)
        self.assertIn("app.old", PS1.split("} finally {")[1])

    def test_shims_never_overwrite_foreign_files(self):
        self.assertIn("Test-OurShim $shim", PS1)
        self.assertIn("Test-OurShim $path", PS1)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def have_tools():
    return all(shutil.which(t) for t in ("curl", "tar", "python3", "sh"))


@unittest.skipUnless(have_tools(), "needs curl, tar, python3")
class TestInstallSh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pb-inst-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        rel = os.path.join(self.tmp, "rel")
        os.mkdir(rel)
        with tarfile.open(os.path.join(rel, "paretobench.tar.gz"), "w:gz") as t:
            for n in ("paretobench", "tasks", "configs", "docs", "pb", "LICENSE"):
                t.add(os.path.join(REPO, n), arcname=n, filter=lambda i: None if "__pycache__" in i.name else i)
        sha = subprocess.run(["python3", "-c",
            "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())",
            os.path.join(rel, "paretobench.tar.gz")], capture_output=True, text=True, check=True).stdout.strip()
        with open(os.path.join(rel, "SHA256SUMS"), "w") as f:
            f.write(f"{sha}  paretobench.tar.gz\n")
        self.rel = rel
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        os.mkdir(self.bin)

    def run_install(self, **extra):
        env = {"PATH": os.environ["PATH"], "HOME": self.tmp, "PARETOBENCH_HOME": self.home,
               "PARETOBENCH_BIN_DIR": self.bin, "PARETOBENCH_RELEASE_BASE": "file://" + self.rel,
               "PARETOBENCH_CONFIG": os.path.join(self.tmp, "models.json")}
        env.update(extra)
        return subprocess.run(["sh", SH], env=env, capture_output=True, text=True)

    def test_foreign_pb_is_left_alone(self):
        pb = os.path.join(self.bin, "pb")
        with open(pb, "w") as f:
            f.write("#!/bin/sh\necho my own pb\n")
        os.chmod(pb, 0o755)
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("my own pb", read(pb))
        self.assertIn("Left", r.stdout)
        self.assertNotIn("written by install", read(pb))
        self.assertTrue(os.path.isfile(os.path.join(self.bin, "paretobench")))
        # Our own shim is upgraded in place on a re-run.
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("written by install.sh", read(os.path.join(self.bin, "paretobench")))

    def test_foreign_paretobench_still_validates(self):
        p = os.path.join(self.bin, "paretobench")
        with open(p, "w") as f:
            f.write("#!/bin/sh\necho other tool\n")
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("other tool", read(p))
        self.assertEqual([n for n in os.listdir(self.bin) if n.startswith(".")], [])

    def test_existing_home_permissions_untouched_and_stage_removed(self):
        os.mkdir(self.home, 0o755)
        os.chmod(self.home, 0o755)
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.stat(self.home).st_mode & 0o777, 0o755)
        self.assertEqual(sorted(os.listdir(self.home)), ["app"])

    def test_new_home_is_private(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.stat(self.home).st_mode & 0o777, 0o700)

    def test_failed_version_check_leaves_no_stage(self):
        with open(os.path.join(self.rel, "SHA256SUMS"), "w") as f:
            f.write("0" * 64 + "  paretobench.tar.gz\n")
        r = self.run_install()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.home, "app")))
        self.assertEqual([n for n in os.listdir(self.home) if n.startswith(".app")] if os.path.isdir(self.home) else [], [])


if __name__ == "__main__":
    unittest.main()
