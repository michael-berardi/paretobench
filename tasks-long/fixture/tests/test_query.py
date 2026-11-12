import unittest

from core.errors import ValidationError
from store import query
from store.models import ENTITIES


def make(n):
    cls = ENTITIES["customer"]
    return [cls(f"cus-{i:04d}", **{f: v for f, v in cls.sample(i).items()}) for i in range(n)]


class TestQuery(unittest.TestCase):
    def test_select_orders_and_slices(self):
        recs = make(6)
        out = query.select(recs, order="-id", limit=2, offset=1)
        self.assertEqual([r.id for r in out], ["cus-0004", "cus-0003"])

    def test_select_negative_offset(self):
        with self.assertRaises(ValidationError):
            query.select(make(2), offset=-1)

    def test_count_by(self):
        recs = make(4)
        self.assertEqual(sum(query.count_by(recs, "id").values()), 4)

    def test_page_size_defaults(self):
        self.assertEqual(query.page_size(None), 25)
        self.assertEqual(query.page_size(7), 7)
        with self.assertRaises(ValidationError):
            query.page_size(0)


if __name__ == "__main__":
    unittest.main()
