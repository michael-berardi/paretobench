"""Route a request dict to a handler and wrap the outcome as {"status", "body"}."""
from api import schema
from api.handlers import HANDLERS
from core.errors import ConflictError, NotFound, ValidationError
from store import orders


def _ok(body):
    return {"status": 200, "body": body}


def _err(status, message):
    return {"status": status, "body": {"error": str(message)}}


def handle(request, registry):
    try:
        op = schema.check_request(request)
        if op == "health":
            return _ok({"ok": True})
        if op == "order_total":
            return _ok(handle_order_total(request))
        entity = request["entity"]
        handler = HANDLERS.get(entity)
        if handler is None:
            raise NotFound(f"unknown entity: {entity}")
        if op == "get":
            return _ok(handler.fetch(registry, request["id"]))
        if op == "put":
            return _ok(handler.create(registry, request["record"]))
        if op == "delete":
            return _ok(handler.remove(registry, request["id"]))
        if op == "list":
            return _ok({"items": handler.list_all(registry)})
    except ValidationError as e:
        return _err(400, e)
    except NotFound as e:
        return _err(404, e)
    except ConflictError as e:
        return _err(409, e)
    return _err(400, "unhandled op")


def handle_order_total(request):
    from api.handlers import orders as order_handler
    return order_handler.order_total(request)


__all__ = ["handle", "orders"]
