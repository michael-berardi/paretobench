import unittest

from core.errors import NotFound
from plugins import registry


class TestToggle(unittest.TestCase):
    def setUp(self):
        registry.load_all()
        self.addCleanup(lambda: [registry.enable(n) for n in list(registry.PLUGINS)])

    def test_disable_and_enable(self):
        name = registry.enabled()[0].name
        registry.disable(name)
        self.assertNotIn(name, [p.name for p in registry.enabled()])
        registry.enable(name)
        self.assertIn(name, [p.name for p in registry.enabled()])

    def test_unknown_names(self):
        with self.assertRaises(NotFound):
            registry.disable("no-such-plugin")
        with self.assertRaises(NotFound):
            registry.enable("no-such-plugin")

    def test_chain_report_lists_handlers_in_order(self):
        for kind in ("shipment", "invoice", "claim"):
            want = [p.name for p in registry.enabled() if kind in p.kinds]
            self.assertEqual(registry.chain_report({"kind": kind}), want)
            self.assertTrue(want)
        self.assertEqual(registry.chain_report({"kind": "no-such-kind"}), [])

    def test_disabled_plugin_leaves_the_report_and_the_chain(self):
        rep = registry.chain_report({"kind": "shipment"})
        registry.disable(rep[0])
        self.assertEqual(registry.chain_report({"kind": "shipment"}), rep[1:])

    def test_chain_report_does_not_run_plugins(self):
        event = {"kind": "shipment", "amount_cents": 1000}
        registry.chain_report(event)
        self.assertEqual(event, {"kind": "shipment", "amount_cents": 1000})


if __name__ == "__main__":
    unittest.main()
