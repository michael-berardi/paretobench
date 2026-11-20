import json
import os
import tempfile
import unittest

from paretobench.config import PBError
from paretobench.harnesses import steak_pi


def make_pkg(root, name="steak-pi"):
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "package.json"), "w") as f:
        json.dump({"name": name, "version": "9.9.9"}, f)
    return root


class SteakPiPackage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = os.path.join(self.tmp.name, "agent")
        os.makedirs(self.agent)

    def settings(self, packages):
        with open(os.path.join(self.agent, "settings.json"), "w") as f:
            json.dump({"packages": packages}, f)

    def test_pinned_package_wins_when_present(self):
        pinned = make_pkg(os.path.join(self.tmp.name, "pinned"))
        self.settings([make_pkg(os.path.join(self.tmp.name, "installed"))])
        self.assertEqual(steak_pi.resolve_package({"steak_pi_package": pinned, "pi_agent_dir": self.agent}), pinned)

    def test_pruned_pin_falls_back_to_the_installed_package(self):
        installed = make_pkg(os.path.join(self.tmp.name, "releases", "0.38.2", "package"))
        self.settings([installed])
        ex = {"steak_pi_package": os.path.join(self.tmp.name, "releases", "0.29.0", "package"), "pi_agent_dir": self.agent}
        steak_pi._validate_package(ex)
        self.assertEqual(ex["steak_pi_package"], installed)
        self.assertEqual(steak_pi.packages(ex), [installed])

    def test_unset_pin_uses_the_installed_package(self):
        installed = make_pkg(os.path.join(self.tmp.name, "inst"))
        self.settings([installed])
        self.assertEqual(steak_pi.resolve_package({"steak_pi_package": "", "pi_agent_dir": self.agent}), installed)

    def test_nothing_usable_is_a_named_error(self):
        self.settings([make_pkg(os.path.join(self.tmp.name, "other"), name="not-steak")])  # not Steak Pi: never picked up
        with self.assertRaises(PBError) as caught:
            steak_pi._validate_package({"steak_pi_package": "/nope", "pi_agent_dir": self.agent})
        self.assertEqual(caught.exception.name, "steak-pi-package-missing")


if __name__ == "__main__":
    unittest.main()
