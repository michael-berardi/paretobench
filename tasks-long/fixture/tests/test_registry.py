import unittest

from plugins import registry


class TestPluginRegistry(unittest.TestCase):
    def test_load_and_order(self):
        n = registry.load_all()
        self.assertGreater(n, 10)
        pri = [p.priority for p in registry.enabled()]
        self.assertEqual(pri, sorted(pri))

    def test_chain_keeps_unhandled_events(self):
        registry.load_all()
        event = {"kind": "no-such-kind", "x": 1}
        self.assertEqual(registry.run_chain(event), event)


if __name__ == "__main__":
    unittest.main()
