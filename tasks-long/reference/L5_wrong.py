# a thin test module that only repeats the happy paths
from _ref import *

write("tests/test_pricing_suite.py", '''import unittest

from core import pricing


class TestThin(unittest.TestCase):
    def test_tier(self):
        self.assertEqual(pricing.apply_tier(20), 5)

    def test_line(self):
        self.assertEqual(pricing.line_total(250, 4), 1000)

    def test_tax(self):
        self.assertEqual(pricing.tax_cents(10000, 2000), 2000)

    def test_ship(self):
        self.assertEqual(pricing.shipping_cents(400, "local"), 500)

    def test_total(self):
        self.assertEqual(pricing.order_total([(1000, 2)], "local", 300)["subtotal"], 2000)

    def test_round(self):
        self.assertEqual(pricing.round_half_even(7, 3), 2)

    def test_cap(self):
        self.assertEqual(pricing.cap_discount(1000, 10), 10)

    def test_tier_top(self):
        self.assertEqual(pricing.apply_tier(500), 15)
''')
