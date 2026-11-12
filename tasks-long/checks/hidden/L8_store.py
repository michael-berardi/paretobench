import unittest

from core.errors import ValidationError
from store.memory import Repository
from store.models import ENTITIES

C = ENTITIES["customer"]


FIELD = C.required[0]  # a required field every customer has


def rec(i, **over):
    return C(f"cus-{i:04d}", **dict(C.sample(i), **over))


class TestBulkPut(unittest.TestCase):
    def test_stores_all_and_returns_count(self):
        repo = Repository(C)
        self.assertEqual(repo.bulk_put([rec(1), rec(2), rec(3)]), 3)
        self.assertEqual(len(repo), 3)

    def test_atomic_failure_stores_nothing(self):
        repo = Repository(C)
        bad = rec(3, **{FIELD: None})
        with self.assertRaises(ValidationError):
            repo.bulk_put([rec(1), rec(2), bad])
        self.assertEqual(len(repo), 0)

    def test_non_atomic_keeps_records_before_the_first_invalid(self):
        repo = Repository(C)
        with self.assertRaises(ValidationError):
            repo.bulk_put([rec(1), rec(2), rec(3, **{FIELD: None}), rec(4)], atomic=False)
        self.assertEqual([r.id for r in repo.all()], ["cus-0001", "cus-0002"])

    def test_validate_false_stores_even_invalid(self):
        repo = Repository(C)
        self.assertEqual(repo.bulk_put([rec(1, **{FIELD: None})], validate=False), 1)

    def test_later_duplicate_wins(self):
        repo = Repository(C)
        repo.bulk_put([C("cus-0001", **C.sample(1)), C("cus-0001", **C.sample(2))])
        self.assertEqual(repo.get("cus-0001").to_dict(), dict(C.sample(2), id="cus-0001"))
        self.assertEqual(len(repo), 1)

    def test_empty_batch(self):
        self.assertEqual(Repository(C).bulk_put([]), 0)


if __name__ == "__main__":
    unittest.main()
