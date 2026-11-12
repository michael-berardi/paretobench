import unittest

from core import pricing
from core.errors import ValidationError


class TestPricingBasics(unittest.TestCase):
    def test_small_quantity_has_no_discount(self):
        self.assertEqual(pricing.apply_tier(5), 0)

    def test_mid_quantity_discount(self):
        self.assertEqual(pricing.apply_tier(20), 5)

    def test_large_quantity_discount(self):
        self.assertEqual(pricing.apply_tier(200), 15)

    def test_line_total_plain(self):
        self.assertEqual(pricing.line_total(250, 4), 1000)

    def test_tax_exclusive(self):
        self.assertEqual(pricing.tax_cents(10000, 2000), 2000)

    def test_shipping_local_light(self):
        self.assertEqual(pricing.shipping_cents(400, "local"), 500)

    def test_unknown_zone(self):
        with self.assertRaises(ValidationError):
            pricing.shipping_cents(100, "moon")

    def test_order_total_runs(self):
        out = pricing.order_total([(1000, 2)], "local", 300)
        self.assertEqual(out["subtotal"], 2000)
        self.assertEqual(out["total"], 2000 + 400 + 500)


if __name__ == "__main__":
    unittest.main()
