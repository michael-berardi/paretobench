import io
import json
import os
import tempfile
import unittest

from cli.main import main
from plugins import registry
from store.models import ENTITIES
from store.registry import Registry

C = ENTITIES["customer"]


def run(argv, reg):
    out = io.StringIO()
    rc = main(argv, registry=reg, out=out)
    return rc, json.loads(out.getvalue())


class TestWaveIntegration(unittest.TestCase):
    def test_log_windows(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.log")
            with open(path, "w") as f:
                f.write("2025-03-04T10:00:01Z GET /a 200 10 5ms\n2025-03-04T10:00:30Z GET /b 200 10 5ms\n"
                        "bad line\n2025-03-04T10:01:10Z GET /a 500 10 5ms\n")
            rc, body = run(["log-windows", path, "--seconds", "60"], Registry())
            self.assertEqual(rc, 0)
            self.assertEqual(body, {"requests": 3, "windows": [["2025-03-04T10:00:00Z", 2],
                                                               ["2025-03-04T10:01:00Z", 1]]})
            rc, body = run(["log-windows", path, "--seconds", "0"], Registry())
            self.assertEqual(rc, 1)
            self.assertIn("error", body)

    def test_plugin_chain(self):
        registry.load_all()
        self.addCleanup(lambda: [registry.enable(n) for n in list(registry.PLUGINS)])
        want = [p.name for p in registry.enabled() if "shipment" in p.kinds]
        rc, body = run(["plugin-chain", "--kind", "shipment"], Registry())
        self.assertEqual((rc, body), (0, {"chain": want}))
        rc, body = run(["plugin-chain", "--kind", "shipment", "--disable", want[0]], Registry())
        self.assertEqual(body, {"chain": want[1:]})
        rc, body = run(["plugin-chain", "--kind", "shipment", "--disable", "nope"], Registry())
        self.assertEqual(rc, 1)
        self.assertIn("error", body)

    def test_put_many_is_atomic_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            good = [dict(id=f"cus-{i:04d}", **C.sample(i)) for i in range(1, 4)]
            rc, body = run(["put-many", "customer", json.dumps(good)], Registry(d))
            self.assertEqual((rc, body), (0, {"stored": 3}))
            self.assertEqual(len(Registry(d).repo("customer")), 3)
            bad = [dict(id="cus-0010", **C.sample(10)), dict(id="cus-0011", **dict(C.sample(11), **{C.required[0]: None}))]
            rc, body = run(["put-many", "customer", json.dumps(bad)], Registry(d))
            self.assertEqual(rc, 1)
            self.assertIn("error", body)
            self.assertEqual(len(Registry(d).repo("customer")), 3)


if __name__ == "__main__":
    unittest.main()
