"""Quotas are stored in a 32-bit column; the API rejects larger limits."""

from app.quota import usage_label

MAX_QUOTA = 2_000_000_000


def label(used: int, raw_limit: int) -> str:
    if not 0 < raw_limit <= MAX_QUOTA:
        raise ValueError("quota out of range")
    return usage_label(used, raw_limit)
