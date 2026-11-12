"""Order pricing on top of core.pricing."""
from core import pricing
from core.errors import ValidationError


def price_order(lines, zone, weight_g, rate_bp=None, coupon_cents=0):
    """lines: list of {"sku": str, "unit_cents": int, "qty": int}."""
    if not isinstance(lines, list) or not lines:
        raise ValidationError("lines must be a non-empty list")
    pairs = []
    for line in lines:
        try:
            pairs.append((line["unit_cents"], line["qty"]))
        except (KeyError, TypeError):
            raise ValidationError("each line needs unit_cents and qty")
    kwargs = {} if rate_bp is None else {"rate_bp": rate_bp}
    return pricing.order_total(pairs, zone, weight_g, coupon_cents=coupon_cents, **kwargs)


def summarize_lines(lines):
    """Units and distinct SKUs on an order (no pricing)."""
    return {"units": sum(l["qty"] for l in lines), "skus": len({l["sku"] for l in lines})}
