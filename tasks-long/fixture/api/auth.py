"""Token checks for the router (not wired into handle(); callers opt in)."""
import hashlib
import hmac

from core.errors import ValidationError


def sign(secret, payload):
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify(secret, payload, signature):
    if not hmac.compare_digest(sign(secret, payload), signature):
        raise ValidationError("bad signature")
    return True
