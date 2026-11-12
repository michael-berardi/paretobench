from _ref import *

ls(".")
read("store/query.py")
read("api/router.py")
read("cli/main.py")
read("docs/api.md")
read("tests/test_router.py")
read("api/schema.py")
grep(r"list_all|\"list\"", ".")

edit("store/query.py", "    return value\n", '''    return value


def paginate(records, limit=None, cursor=None):
    """One page of records ordered by id. cursor is None or 'after:<id>'."""
    size = page_size(limit)
    ordered = sorted(records, key=lambda r: r.id)
    if cursor is not None:
        if not isinstance(cursor, str) or not cursor.startswith("after:") or cursor == "after:":
            raise ValidationError("invalid cursor")
        after = cursor[len("after:"):]
        ordered = [r for r in ordered if r.id > after]
    items = ordered[:size]
    next_cursor = "after:" + items[-1].id if len(ordered) > size else None
    return {"items": items, "next_cursor": next_cursor}
''')
edit("api/router.py", "from store import orders\n", "from store import orders, query\n")
edit("api/router.py", '''        if op == "list":
            return _ok({"items": handler.list_all(registry)})''', '''        if op == "list":
            if "limit" in request or "cursor" in request:
                page = query.paginate(registry.repo(entity).all(), request.get("limit"), request.get("cursor"))
                return _ok({"items": [r.to_dict() for r in page["items"]], "next_cursor": page["next_cursor"]})
            return _ok({"items": handler.list_all(registry)})''')
edit("cli/main.py", '''    s = sub.add_parser("list", help="list the records of an entity")
    s.add_argument("entity")
''', '''    s = sub.add_parser("list", help="list the records of an entity")
    s.add_argument("entity")
    s.add_argument("--limit", type=int, help="page size")
    s.add_argument("--cursor", help="continue after this cursor (from next_cursor)")
''')
edit("cli/main.py", '''        if args.cmd == "put":
            req["record"] = json.loads(args.record)
''', '''        if args.cmd == "put":
            req["record"] = json.loads(args.record)
        if args.cmd == "list":
            if args.limit is not None:
                req["limit"] = args.limit
            if args.cursor is not None:
                req["cursor"] = args.cursor
''')
edit("docs/api.md", "## Command line", '''## Pagination

`list` accepts optional `limit` (1 to 100, default 25) and `cursor`. Records come back ordered by id.
When a limit or cursor is given, the body also carries `next_cursor`: pass it as `cursor` to get the
next page; it is null on the last page. From the command line use `--limit N` and `--cursor C`.

## Command line''')
write("tests/test_pagination.py", '''import unittest

from api.router import handle
from core.errors import ValidationError
from store import query
from store.models import ENTITIES
from store.registry import Registry

C = ENTITIES["customer"]


def recs(n):
    return [C(f"cus-{i:04d}", **C.sample(i)) for i in range(1, n + 1)]


class TestPagination(unittest.TestCase):
    def test_pages_cover_everything_once(self):
        seen, cursor = [], None
        while True:
            page = query.paginate(recs(9), limit=4, cursor=cursor)
            seen += [r.id for r in page["items"]]
            cursor = page["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(seen, [f"cus-{i:04d}" for i in range(1, 10)])

    def test_last_page_has_no_cursor(self):
        self.assertIsNone(query.paginate(recs(4), limit=4)["next_cursor"])

    def test_bad_cursor(self):
        with self.assertRaises(ValidationError):
            query.paginate(recs(3), cursor="nope")

    def test_router_pages(self):
        reg = Registry()
        for r in recs(5):
            handle({"op": "put", "entity": "customer", "record": r.to_dict()}, reg)
        out = handle({"op": "list", "entity": "customer", "limit": 2}, reg)
        self.assertEqual(out["body"]["next_cursor"], "after:cus-0002")

    def test_router_plain_list_unchanged(self):
        out = handle({"op": "list", "entity": "customer"}, Registry())
        self.assertEqual(out["body"], {"items": []})


if __name__ == "__main__":
    unittest.main()
''')
sh("python3 -B -m unittest discover -s tests -t .")
sh("FREIGHT_DATA=data/store python3 -B -m cli list customer --limit 2")
