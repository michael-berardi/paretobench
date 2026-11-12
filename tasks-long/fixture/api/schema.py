"""Request shape checks."""
from core.errors import ValidationError

OPS = {
    "get": ("entity", "id"),
    "put": ("entity", "record"),
    "delete": ("entity", "id"),
    "list": ("entity",),
    "order_total": ("lines", "zone", "weight_g"),
    "health": (),
}


def check_request(request):
    if not isinstance(request, dict) or "op" not in request:
        raise ValidationError("request must be an object with an op")
    op = request["op"]
    if op not in OPS:
        raise ValidationError(f"unknown op: {op!r}")
    missing = [k for k in OPS[op] if k not in request]
    if missing:
        raise ValidationError(f"{op}: missing {', '.join(missing)}")
    return op
