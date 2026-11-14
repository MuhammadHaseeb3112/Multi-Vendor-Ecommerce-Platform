"""Order lookup for the public "track order" pages.

An order is only revealed when the caller proves they own it: the order ID
must match the email on the order, unless the signed-in user placed it
(or is staff).
"""
from .models import Order


def find_trackable_order(request):
    order_id = (request.POST.get("query") or "").strip().lstrip("#")
    email = (request.POST.get("email") or "").strip()
    user = request.user

    if not order_id.isdigit():
        return None

    order = Order.objects.filter(id=int(order_id)).first()
    if order is None:
        return None
    if user.is_authenticated and (user.is_staff or order.user_id == user.id):
        return order
    if email and order.email.lower() == email.lower():
        return order
    return None
