"""Price rules. All amounts are integer cents. This module is the only place prices are computed."""
from core import config
from core.errors import ValidationError

# (minimum quantity, percent discount); the highest tier whose minimum is reached applies
TIERS = ((1, 0), (10, 5), (50, 10), (100, 15))
SHIPPING_RATES = {"local": (500, 2), "national": (900, 4), "intl": (2500, 9)}  # base, per started 100 g over 500 g
MAX_COUPON_PCT = 30


def round_half_even(numerator, denominator):
    """Integer division rounding halves to the even neighbour (banker's rounding)."""
    if denominator <= 0:
        raise ValidationError("denominator must be positive")
    q, r = divmod(numerator, denominator)
    twice = 2 * r
    if twice > denominator or (twice == denominator and q % 2 == 1):
        q += 1
    return q


def apply_tier(qty, tiers=TIERS):
    """Percent discount for a quantity: the highest tier whose minimum quantity is reached."""
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
        raise ValidationError("qty must be an integer of at least 1")
    pct = 0
    for min_qty, tier_pct in tiers:
        if qty >= min_qty:
            pct = tier_pct
    return pct


def line_total(unit_cents, qty, tiers=TIERS):
    """Total for one order line after the quantity discount."""
    if not isinstance(unit_cents, int) or unit_cents < 0:
        raise ValidationError("unit price must be a non-negative integer of cents")
    pct = apply_tier(qty, tiers)
    gross = unit_cents * qty
    discount = round_half_even(gross * pct, 100)
    return gross - discount


def tax_cents(amount, rate_bp, inclusive=False):
    """Tax on an amount. rate_bp is in basis points. With inclusive=True the amount already contains the tax."""
    if rate_bp < 0:
        raise ValidationError("tax rate must not be negative")
    if inclusive:
        return amount - round_half_even(amount * 10000, 10000 + rate_bp)
    return round_half_even(amount * rate_bp, 10000)


def shipping_cents(weight_g, zone):
    """Shipping: a base fee covers the first 500 g, then a fee per started 100 g."""
    if zone not in SHIPPING_RATES:
        raise ValidationError(f"unknown zone: {zone!r}")
    if weight_g <= 0:
        raise ValidationError("weight must be positive")
    base, per_100 = SHIPPING_RATES[zone]
    extra = max(0, weight_g - 500)
    started = -(-extra // 100)
    return base + started * per_100


def cap_discount(subtotal, coupon_cents, max_pct=MAX_COUPON_PCT):
    """A coupon never takes more than max_pct percent of the subtotal."""
    if coupon_cents < 0:
        raise ValidationError("coupon must not be negative")
    return min(coupon_cents, subtotal * max_pct // 100)


def order_total(lines, zone, weight_g, rate_bp=config.DEFAULT_TAX_BP, coupon_cents=0):
    """Price a whole order. lines: list of (unit_cents, qty). Returns the breakdown as a dict."""
    if not lines:
        raise ValidationError("an order needs at least one line")
    subtotal = sum(line_total(u, q) for u, q in lines)
    coupon = cap_discount(subtotal, coupon_cents)
    taxable = subtotal - coupon
    tax = tax_cents(taxable, rate_bp)
    shipping = 0 if subtotal >= config.FREE_SHIPPING_CENTS else shipping_cents(weight_g, zone)
    return {"subtotal": subtotal, "coupon": coupon, "tax": tax, "shipping": shipping,
            "total": taxable + tax + shipping}
