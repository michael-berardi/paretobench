import unittest

from api.router import handle
from store.models import ENTITIES
from store.registry import Registry


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.reg = Registry()

    def put(self, i):
        cls = ENTITIES["customer"]
        return handle({"op": "put", "entity": "customer",
                       "record": dict(id=f"cus-{i:04d}", **cls.sample(i))}, self.reg)

    def test_health(self):
        self.assertEqual(handle({"op": "health"}, self.reg), {"status": 200, "body": {"ok": True}})

    def test_put_get_list_delete(self):
        self.assertEqual(self.put(3)["status"], 200)
        self.put(1)
        got = handle({"op": "get", "entity": "customer", "id": "cus-0003"}, self.reg)
        self.assertEqual(got["body"]["id"], "cus-0003")
        listed = handle({"op": "list", "entity": "customer"}, self.reg)
        self.assertEqual([r["id"] for r in listed["body"]["items"]], ["cus-0001", "cus-0003"])
        gone = handle({"op": "delete", "entity": "customer", "id": "cus-0003"}, self.reg)
        self.assertEqual(gone["body"], {"deleted": "cus-0003"})

    def test_errors(self):
        self.assertEqual(handle({"op": "nope"}, self.reg)["status"], 400)
        self.assertEqual(handle({"op": "get", "entity": "customer", "id": "cus-0009"}, self.reg)["status"], 404)
        self.assertEqual(handle({"op": "get", "entity": "ghost", "id": "x-0001"}, self.reg)["status"], 404)
        self.assertEqual(handle({"op": "get"}, self.reg)["status"], 400)

    def test_order_total(self):
        r = handle({"op": "order_total", "lines": [{"sku": "A", "unit_cents": 1000, "qty": 2}],
                    "zone": "local", "weight_g": 300}, self.reg)
        self.assertEqual(r["status"], 200)
        self.assertEqual(r["body"]["subtotal"], 2000)


if __name__ == "__main__":
    unittest.main()
