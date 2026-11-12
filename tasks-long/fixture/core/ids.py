"""Record ids look like '<prefix>-<4+ digits>'. Sorting ids as strings sorts them by number."""
import re

from core.errors import ValidationError

_ID = re.compile(r"^[a-z]{2,4}-\d{4,}$")


def make_id(prefix, n):
    if not (isinstance(n, int) and n >= 0):
        raise ValidationError("id number must be a non-negative integer")
    return f"{prefix}-{n:04d}"


def check_id(value, prefix=None):
    if not isinstance(value, str) or not _ID.match(value):
        raise ValidationError(f"bad id: {value!r}")
    if prefix and not value.startswith(prefix + "-"):
        raise ValidationError(f"id {value!r} does not start with {prefix}-")
    return value
