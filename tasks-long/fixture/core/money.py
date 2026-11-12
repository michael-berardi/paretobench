"""Money helpers. Amounts are integer cents."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from core.errors import ValidationError


def to_cents(value):
    """Convert '12.34', 12.34, Decimal('12.34') or an int number of euros to integer cents."""
    if isinstance(value, bool):
        raise ValidationError("not an amount")
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(f"not an amount: {value!r}")
    return int((d * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def round_half_up(numerator, denominator):
    """Integer division rounding halves away from zero (used for display rounding only)."""
    if denominator <= 0:
        raise ValidationError("denominator must be positive")
    q, r = divmod(abs(numerator), denominator)
    if 2 * r >= denominator:
        q += 1
    return q if numerator >= 0 else -q
