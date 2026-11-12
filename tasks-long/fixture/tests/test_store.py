import os
import tempfile
import unittest

from core.errors import ConflictError, NotFound, ValidationError
from store.index import SecondaryIndex
from store.memory import Repository
from store.models import ENTITIES
from store.registry import Registry

Customer = ENTITIES["customer"]


class TestRepository(unittest.TestCase):
    def test_put_get_delete(self):
        repo = Repository(Customer)
        rec = Customer("cus-0001", **Customer.sample(1))
        repo.put(rec, validate=True)
        self.assertIs(repo.get("cus-0001"), rec)
        repo.delete("cus-0001")
        with self.assertRaises(NotFound):
            repo.get("cus-0001")

    def test_no_overwrite(self):
        repo = Repository(Customer)
        repo.put(Customer("cus-0001", **Customer.sample(1)))
        with self.assertRaises(ConflictError):
            repo.put(Customer("cus-0001", **Customer.sample(2)), overwrite=False)

    def test_validation_rejects_bad_id(self):
        repo = Repository(Customer)
        with self.assertRaises(ValidationError):
            repo.put(Customer("nope", **Customer.sample(1)), validate=True)

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Registry(d)
            reg.repo("customer").put(Customer("cus-0002", **Customer.sample(2)))
            reg.save_all()
            self.assertTrue(os.path.isfile(os.path.join(d, "customer.json")))
            again = Registry(d)
            self.assertEqual(again.repo("customer").get("cus-0002").to_dict()["id"], "cus-0002")

    def test_index(self):
        idx = SecondaryIndex("id")
        recs = [Customer(f"cus-{i:04d}", **Customer.sample(i)) for i in range(3)]
        for r in recs:
            idx.add(r)
        self.assertEqual(idx.lookup("cus-0001"), ["cus-0001"])
        idx.remove(recs[1])
        self.assertEqual(idx.lookup("cus-0001"), [])


if __name__ == "__main__":
    unittest.main()
