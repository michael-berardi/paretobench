import unittest

from store.index import SecondaryIndex


class Item:
    def __init__(self, id, color):
        self.id, self.color = id, color


class TestIndex(unittest.TestCase):
    def test_remove_drops_empty_keys_only(self):
        idx = SecondaryIndex("color")
        a, b, c = Item("x-0001", "red"), Item("x-0002", "red"), Item("x-0003", "blue")
        for r in (a, b, c):
            idx.add(r)
        idx.remove(a)
        self.assertEqual(idx.keys(), ["blue", "red"])
        self.assertEqual(idx.lookup("red"), ["x-0002"])
        idx.remove(b)
        self.assertEqual(idx.keys(), ["blue"])
        idx.remove(c)
        self.assertEqual(idx.keys(), [])

    def test_removing_unknown_record_is_a_no_op(self):
        idx = SecondaryIndex("color")
        idx.remove(Item("x-0009", "green"))
        self.assertEqual(idx.keys(), [])

    def test_rebuild_forgets_old_entries(self):
        idx = SecondaryIndex("color")
        idx.add(Item("x-0001", "red"))
        self.assertEqual(idx.rebuild([Item("x-0002", "blue")]), 1)
        self.assertEqual(idx.lookup("red"), [])


if __name__ == "__main__":
    unittest.main()
