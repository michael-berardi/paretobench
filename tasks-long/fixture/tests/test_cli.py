import io
import json
import tempfile
import unittest

from cli.main import main
from store.models import ENTITIES
from store.registry import Registry


class TestCli(unittest.TestCase):
    def run_cli(self, argv, reg):
        out = io.StringIO()
        rc = main(argv, registry=reg, out=out)
        return rc, json.loads(out.getvalue())

    def test_put_then_list(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Registry(d)
            rec = json.dumps(dict(id="cus-0001", **ENTITIES["customer"].sample(1)))
            rc, body = self.run_cli(["put", "customer", rec], reg)
            self.assertEqual(rc, 0)
            rc, body = self.run_cli(["list", "customer"], Registry(d))
            self.assertEqual([r["id"] for r in body["items"]], ["cus-0001"])

    def test_get_missing(self):
        rc, body = self.run_cli(["get", "customer", "cus-0042"], Registry())
        self.assertEqual(rc, 1)
        self.assertIn("not found", body["error"])

    def test_entity_command(self):
        reg = Registry()
        reg.repo("customer").put(ENTITIES["customer"]("cus-0001", **ENTITIES["customer"].sample(1)))
        rc, body = self.run_cli(["customer-show", "cus-0001"], reg)
        self.assertEqual(rc, 0)
        self.assertEqual(body["id"], "cus-0001")


if __name__ == "__main__":
    unittest.main()
