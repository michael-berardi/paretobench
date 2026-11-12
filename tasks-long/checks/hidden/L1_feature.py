import io
import json
import tempfile
import unittest

from api.router import handle
from cli.main import main
from core.errors import ValidationError
from store import query
from store.models import ENTITIES
from store.registry import Registry

C = ENTITIES["customer"]


def recs(n):
    return [C(f"cus-{i:04d}", **C.sample(i)) for i in range(1, n + 1)]


def ids(items):
    return [getattr(r, "id", None) or r["id"] for r in items]


class TestPaginate(unittest.TestCase):
    def test_first_page(self):
        r = query.paginate(recs(7), limit=3)
        self.assertEqual(ids(r["items"]), ["cus-0001", "cus-0002", "cus-0003"])
        self.assertEqual(r["next_cursor"], "after:cus-0003")

    def test_following_the_cursor_returns_everything_once(self):
        seen, cursor, pages = [], None, 0
        while True:
            r = query.paginate(recs(11), limit=4, cursor=cursor)
            seen += ids(r["items"])
            pages += 1
            cursor = r["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(seen, [f"cus-{i:04d}" for i in range(1, 12)])
        self.assertEqual(pages, 3)

    def test_exact_boundary_has_no_next_cursor(self):
        r = query.paginate(recs(6), limit=3, cursor="after:cus-0003")
        self.assertEqual(ids(r["items"]), ["cus-0004", "cus-0005", "cus-0006"])
        self.assertIsNone(r["next_cursor"])

    def test_input_order_does_not_matter(self):
        r = query.paginate(list(reversed(recs(5))), limit=2)
        self.assertEqual(ids(r["items"]), ["cus-0001", "cus-0002"])

    def test_cursor_past_the_end(self):
        r = query.paginate(recs(3), limit=2, cursor="after:cus-9999")
        self.assertEqual(r, {"items": [], "next_cursor": None})

    def test_default_limit_is_the_default_page_size(self):
        r = query.paginate(recs(30))
        self.assertEqual(len(r["items"]), 25)
        self.assertEqual(r["next_cursor"], "after:cus-0025")

    def test_limit_bounds(self):
        self.assertEqual(len(query.paginate(recs(120), limit=100)["items"]), 100)
        for bad in (0, -1, 101, "5", True, 2.5):
            with self.assertRaises(ValidationError):
                query.paginate(recs(3), limit=bad)

    def test_invalid_cursors(self):
        for bad in ("foo", "after:", "AFTER:cus-0001", "", 5, "after", "before:cus-0001"):
            with self.assertRaises(ValidationError) as cm:
                query.paginate(recs(3), limit=2, cursor=bad)
            self.assertEqual(str(cm.exception), "invalid cursor")


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.reg = Registry()
        for r in recs(7):
            handle({"op": "put", "entity": "customer", "record": r.to_dict()}, self.reg)

    def test_paged_list(self):
        r = handle({"op": "list", "entity": "customer", "limit": 3}, self.reg)
        self.assertEqual(r["status"], 200)
        self.assertEqual(ids(r["body"]["items"]), ["cus-0001", "cus-0002", "cus-0003"])
        self.assertEqual(r["body"]["next_cursor"], "after:cus-0003")
        r = handle({"op": "list", "entity": "customer", "limit": 3, "cursor": "after:cus-0006"}, self.reg)
        self.assertEqual(ids(r["body"]["items"]), ["cus-0007"])
        self.assertIsNone(r["body"]["next_cursor"])

    def test_plain_list_is_unchanged(self):
        r = handle({"op": "list", "entity": "customer"}, self.reg)
        self.assertEqual(set(r["body"]), {"items"})
        self.assertEqual(len(r["body"]["items"]), 7)

    def test_cursor_alone_uses_default_limit(self):
        r = handle({"op": "list", "entity": "customer", "cursor": "after:cus-0002"}, self.reg)
        self.assertEqual(len(r["body"]["items"]), 5)
        self.assertIsNone(r["body"]["next_cursor"])

    def test_bad_parameters_are_400(self):
        r = handle({"op": "list", "entity": "customer", "cursor": "nonsense"}, self.reg)
        self.assertEqual(r, {"status": 400, "body": {"error": "invalid cursor"}})
        for bad in (0, "3", 101):
            self.assertEqual(handle({"op": "list", "entity": "customer", "limit": bad}, self.reg)["status"], 400)


class TestCli(unittest.TestCase):
    def run_cli(self, argv, reg):
        out = io.StringIO()
        rc = main(argv, registry=reg, out=out)
        return rc, json.loads(out.getvalue())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        reg = Registry(self.tmp.name)
        for r in recs(5):
            reg.repo("customer").put(r)
        reg.save_all()

    def test_limit_and_cursor(self):
        rc, body = self.run_cli(["list", "customer", "--limit", "2"], Registry(self.tmp.name))
        self.assertEqual(rc, 0)
        self.assertEqual(ids(body["items"]), ["cus-0001", "cus-0002"])
        self.assertEqual(body["next_cursor"], "after:cus-0002")
        rc, body = self.run_cli(["list", "customer", "--limit", "2", "--cursor", "after:cus-0004"],
                                Registry(self.tmp.name))
        self.assertEqual(ids(body["items"]), ["cus-0005"])
        self.assertIsNone(body["next_cursor"])

    def test_plain_list(self):
        rc, body = self.run_cli(["list", "customer"], Registry(self.tmp.name))
        self.assertEqual((rc, set(body), len(body["items"])), (0, {"items"}, 5))

    def test_bad_cursor(self):
        rc, body = self.run_cli(["list", "customer", "--cursor", "zzz"], Registry(self.tmp.name))
        self.assertEqual((rc, body), (1, {"error": "invalid cursor"}))


if __name__ == "__main__":
    unittest.main()
