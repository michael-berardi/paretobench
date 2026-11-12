"""Order pricing handler."""
from store import orders


def order_total(request):
    return orders.price_order(request["lines"], request["zone"], request["weight_g"],
                              rate_bp=request.get("rate_bp"),
                              coupon_cents=request.get("coupon_cents", 0))
