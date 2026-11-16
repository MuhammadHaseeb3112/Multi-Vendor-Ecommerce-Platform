"""Public demo helpers (only active when DEMO_MODE=True).

Every visitor who clicks "Customer" on the login page gets a private,
throw-away customer account with a copy of the sample orders, so two
recruiters browsing at the same time never see each other's cart or
orders. The nightly `seed_demo --reset` removes these accounts.
"""
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import Cart, Order, OrderItem, Payment
from .ratelimit import client_ip

User = get_user_model()
TEMPLATE_CUSTOMER = "demo_customer"
MAX_VISITORS_PER_IP_PER_HOUR = 20


def _create_visitor():
    template = User.objects.filter(username=TEMPLATE_CUSTOMER).first()
    username = f"visitor_{secrets.token_hex(4)}"
    user = User(
        username=username, email=f"{username}@example.com",
        first_name="Demo", last_name="Visitor",
        address=getattr(template, "address", "") or "House 12, Street 4, Lahore",
        phone="0300 0000000",
    )
    user.set_unusable_password()
    user.save()

    if template:
        # Copy the sample order history so the dashboard isn't empty.
        for order in Order.objects.filter(user=template).order_by("created_at"):
            items = list(order.items.all())
            payment = Payment.objects.filter(order=order).first()
            created_at = order.created_at
            order.pk = None
            order.id = None
            order._state.adding = True
            order.user = user
            order.full_name = user.get_full_name()
            order.email = user.email
            order.save()
            Order.objects.filter(pk=order.pk).update(created_at=created_at)
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product_id=i.product_id, color=i.color,
                          size=i.size, price=i.price, quantity=i.quantity)
                for i in items
            ])
            if payment:
                Payment.objects.create(order=order, card_number=payment.card_number,
                                       expiry=payment.expiry, cvv="",
                                       payment_status=payment.payment_status)
    return user


@require_POST
def demo_customer_login(request):
    if not settings.DEMO_MODE:
        raise Http404

    key = f"demo-visitors:{client_ip(request)}"
    if cache.get(key, 0) >= MAX_VISITORS_PER_IP_PER_HOUR:
        messages.warning(request, "Too many demo accounts from your network. Please try again later.")
        return redirect("login")

    guest_session_key = request.session.session_key
    with transaction.atomic():
        user = _create_visitor()
    if not cache.add(key, 1, 3600):
        cache.incr(key)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    guest_cart = (
        Cart.objects.filter(session_key=guest_session_key, user=None).first()
        if guest_session_key else None
    )
    if guest_cart:
        Cart.for_user(user).merge_with(guest_cart)

    messages.success(request, "Welcome! This is your own private demo account. Shop freely.")
    return redirect("customer_dashboard")
