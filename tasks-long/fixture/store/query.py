"""Filtering and ordering over lists of records."""
from core import config
from core.errors import ValidationError


def where(records, **equals):
    """Records whose attributes equal every given value."""
    return [r for r in records if all(getattr(r, k, None) == v for k, v in equals.items())]


def order_by(records, field, descending=False):
    return sorted(records, key=lambda r: (getattr(r, field) is None, getattr(r, field)), reverse=descending)


def select(records, filters=None, order=None, limit=None, offset=0):
    """Filter, order, then slice. limit None means no limit."""
    out = where(records, **(filters or {}))
    if order:
        out = order_by(out, order.lstrip("-"), descending=order.startswith("-"))
    if offset < 0:
        raise ValidationError("offset must not be negative")
    out = out[offset:]
    return out if limit is None else out[:limit]


def count_by(records, field):
    counts = {}
    for r in records:
        key = getattr(r, field)
        counts[key] = counts.get(key, 0) + 1
    return counts


def page_size(value):
    """Validate a requested page size."""
    if value is None:
        return config.DEFAULT_PAGE_SIZE
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= config.MAX_PAGE_SIZE:
        raise ValidationError(f"limit must be an integer from 1 to {config.MAX_PAGE_SIZE}")
    return value
