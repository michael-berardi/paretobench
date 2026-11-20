import json
import os
import tempfile
import unittest

from paretobench.harnesses import pi


class LaneAgentDirLocalModels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = os.path.join(self.tmp.name, "agent")
        os.makedirs(self.agent)
        for name in ("auth.json", "models.json"):
            with open(os.path.join(self.agent, name), "w") as f:
                json.dump({}, f)
        self.work = os.path.join(self.tmp.name, "work")

    def test_lane_sees_the_operators_local_models(self):
        os.makedirs(os.path.join(self.agent, "local", "profiles"))
        lane = pi.make_agent_dir({"pi_agent_dir": self.agent}, self.work, 0, "steak-pi", [])
        local = os.path.join(lane["agent_dir"], "local")
        self.assertTrue(os.path.islink(local))
        self.assertTrue(os.path.isdir(os.path.join(local, "profiles")))

    def test_no_local_folder_adds_nothing(self):
        lane = pi.make_agent_dir({"pi_agent_dir": self.agent}, self.work, 0, "pi", [])
        self.assertFalse(os.path.lexists(os.path.join(lane["agent_dir"], "local")))


if __name__ == "__main__":
    unittest.main()
