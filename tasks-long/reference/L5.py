from _ref import *

ls("tests")
read("core/pricing.py")
grep(r"pricing", ".")
read("tests/test_pricing.py")
read("core/config.py")
read("core/errors.py")
write("tests/test_pricing_suite.py", '''import unittest

from core import config, pricing
from core.errors import ValidationError


class TestRoundHalfEven(unittest.TestCase):
    def test_ties_go_to_the_even_neighbour(self):
        self.assertEqual(pricing.round_half_even(1, 2), 0)
        self.assertEqual(pricing.round_half_even(3, 2), 2)
        self.assertEqual(pricing.round_half_even(5, 2), 2)
        self.assertEqual(pricing.round_half_even(7, 2), 4)
        self.assertEqual(pricing.round_half_even(10, 4), 2)

    def test_non_ties_round_to_nearest(self):
        self.assertEqual(pricing.round_half_even(7, 3), 2)
        self.assertEqual(pricing.round_half_even(8, 3), 3)
        self.assertEqual(pricing.round_half_even(0, 5), 0)

    def test_denominator_must_be_positive(self):
        for d in (0, -1):
            with self.assertRaises(ValidationError):
                pricing.round_half_even(1, d)


class TestApplyTier(unittest.TestCase):
    def test_every_boundary(self):
        cases = {1: 0, 9: 0, 10: 5, 11: 5, 49: 5, 50: 10, 99: 10, 100: 15, 500: 15}
        for qty, pct in cases.items():
            self.assertEqual(pricing.apply_tier(qty), pct, qty)

    def test_custom_tiers(self):
        self.assertEqual(pricing.apply_tier(5, ((1, 0), (5, 7))), 7)
        self.assertEqual(pricing.apply_tier(4, ((1, 0), (5, 7))), 0)

    def test_invalid_quantities(self):
        for bad in (0, -1, True, 1.5, "3"):
            with self.assertRaises(ValidationError):
                pricing.apply_tier(bad)


class TestLineTotal(unittest.TestCase):
    def test_plain_and_discounted(self):
        self.assertEqual(pricing.line_total(250, 4), 1000)
        self.assertEqual(pricing.line_total(1000, 10), 9500)
        self.assertEqual(pricing.line_total(1000, 100), 85000)

    def test_discount_rounds_half_even(self):
        self.assertEqual(pricing.line_total(1003, 10), 9528)   # 501.5 rounds to 502
        self.assertEqual(pricing.line_total(1007, 10), 9566)   # 503.5 rounds to 504
        self.assertEqual(pricing.line_total(1005, 10), 9548)   # 502.5 rounds to 502

    def test_invalid_unit_price(self):
        for bad in (-1, 1.5):
            with self.assertRaises(ValidationError):
                pricing.line_total(bad, 2)


class TestTax(unittest.TestCase):
    def test_exclusive(self):
        self.assertEqual(pricing.tax_cents(10000, 2000), 2000)
        self.assertEqual(pricing.tax_cents(999, 1000), 100)

    def test_inclusive(self):
        self.assertEqual(pricing.tax_cents(12000, 2000, inclusive=True), 2000)
        self.assertEqual(pricing.tax_cents(11000, 1000, inclusive=True), 1000)

    def test_negative_rate(self):
        with self.assertRaises(ValidationError):
            pricing.tax_cents(100, -1)


class TestShipping(unittest.TestCase):
    def test_first_500_grams_cost_the_base_fee(self):
        self.assertEqual(pricing.shipping_cents(1, "local"), 500)
        self.assertEqual(pricing.shipping_cents(500, "local"), 500)

    def test_every_started_100_grams_over_500_cost_extra(self):
        self.assertEqual(pricing.shipping_cents(501, "local"), 502)
        self.assertEqual(pricing.shipping_cents(600, "local"), 502)
        self.assertEqual(pricing.shipping_cents(601, "local"), 504)

    def test_zone_rates(self):
        self.assertEqual(pricing.shipping_cents(1000, "national"), 920)
        self.assertEqual(pricing.shipping_cents(1000, "intl"), 2545)

    def test_invalid_input(self):
        for args in ((100, "moon"), (0, "local"), (-5, "local")):
            with self.assertRaises(ValidationError):
                pricing.shipping_cents(*args)


class TestCoupon(unittest.TestCase):
    def test_cap_and_passthrough(self):
        self.assertEqual(pricing.cap_discount(10000, 5000), 3000)
        self.assertEqual(pricing.cap_discount(10000, 100), 100)
        self.assertEqual(pricing.cap_discount(1000, 999, max_pct=10), 100)

    def test_negative_coupon(self):
        with self.assertRaises(ValidationError):
            pricing.cap_discount(1000, -1)


class TestOrderTotal(unittest.TestCase):
    def test_free_shipping_starts_exactly_at_the_threshold(self):
        at = pricing.order_total([(config.FREE_SHIPPING_CENTS, 1)], "local", 300)
        self.assertEqual(at["shipping"], 0)
        below = pricing.order_total([(config.FREE_SHIPPING_CENTS - 1, 1)], "local", 300)
        self.assertEqual(below["shipping"], 500)

    def test_breakdown(self):
        out = pricing.order_total([(20000, 1)], "local", 300)
        self.assertEqual(out, {"subtotal": 20000, "coupon": 0, "tax": 4000, "shipping": 0, "total": 24000})

    def test_coupon_is_capped_before_tax(self):
        out = pricing.order_total([(20000, 1)], "local", 300, coupon_cents=7000)
        self.assertEqual(out["coupon"], 6000)
        self.assertEqual((out["tax"], out["total"]), (2800, 16800))

    def test_needs_lines(self):
        with self.assertRaises(ValidationError):
            pricing.order_total([], "local", 300)


if __name__ == "__main__":
    unittest.main()
''')
sh("python3 -B -m unittest tests.test_pricing_suite")
sh("python3 - <<'PY'\nimport shutil, subprocess, sys, tempfile, os\nd = tempfile.mkdtemp()\nshutil.copytree('core', d + '/core')\nshutil.copytree('tests', d + '/tests', ignore=shutil.ignore_patterns('__pycache__'))\np = d + '/core/pricing.py'\nt = open(p).read().replace('if qty >= min_qty:', 'if qty > min_qty:')\nopen(p, 'w').write(t)\nr = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'tests.test_pricing_suite'], cwd=d, capture_output=True)\nshutil.rmtree(d)\nsys.exit(0 if r.returncode != 0 else 1)\nPY")
sh("python3 -B -m unittest discover -s tests -t .")
