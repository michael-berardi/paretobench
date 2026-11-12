import unittest

from api.router import handle
from core import pricing
from core.errors import ValidationError
from store.registry import Registry


class TestTierBoundaries(unittest.TestCase):
    def test_every_boundary(self):
        cases = {1: 0, 2: 0, 9: 0, 10: 5, 11: 5, 49: 5, 50: 10, 51: 10, 99: 10, 100: 15, 101: 15, 1000: 15}
        for qty, pct in cases.items():
            self.assertEqual(pricing.apply_tier(qty), pct, qty)

    def test_custom_tiers(self):
        tiers = ((1, 0), (5, 7))
        self.assertEqual(pricing.apply_tier(4, tiers), 0)
        self.assertEqual(pricing.apply_tier(5, tiers), 7)

    def test_line_totals_at_thresholds(self):
        self.assertEqual(pricing.line_total(1000, 10), 9500)
        self.assertEqual(pricing.line_total(1000, 50), 45000)
        self.assertEqual(pricing.line_total(1000, 100), 85000)
        self.assertEqual(pricing.line_total(1000, 9), 9000)

    def test_router_at_each_threshold(self):
        for qty, want in ((10, 9500), (50, 45000), (100, 85000), (49, 46550)):
            r = handle({"op": "order_total", "lines": [{"sku": "A-1", "unit_cents": 1000, "qty": qty}],
                        "zone": "local", "weight_g": 300}, Registry())
            self.assertEqual(r["body"]["subtotal"], want, qty)

    def test_invalid_quantity_still_rejected(self):
        for bad in (0, -3, True, 2.0):
            with self.assertRaises(ValidationError):
                pricing.apply_tier(bad)

    def test_other_price_rules_untouched(self):
        self.assertEqual(pricing.tax_cents(10000, 2000), 2000)
        self.assertEqual(pricing.shipping_cents(500, "local"), 500)
        self.assertEqual(pricing.shipping_cents(501, "local"), 502)
        self.assertEqual(pricing.round_half_even(5, 2), 2)
        self.assertEqual(pricing.round_half_even(7, 2), 4)


if __name__ == "__main__":
    unittest.main()
