"""Public demo: one-click private accounts (only when DEMO_MODE=True).

"Customer" and "Vendor" on the login page each create a throw-away visitor
account. A visitor vendor gets a private copy of the demo store (products,
variants, orders, earnings) that they can fully manage. Everything they
create is hidden from other visitors (see api/sandbox.py), and the nightly
`seed_demo --reset` removes it all.
"""
import secrets
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import (
    Cart, Order, OrderItem, Payment, Product, ProductColorVariant, ProductSizeVariant,
    Vendor, Withdrawal,
)
from .ratelimit import client_ip
from .sandbox import VISITOR_PREFIX

User = get_user_model()
TEMPLATE_CUSTOMER = "demo_customer"
TEMPLATE_VENDOR = "demo_vendor"
MAX_VISITORS_PER_IP_PER_HOUR = 20


def _new_user(**extra):
    username = f"{VISITOR_PREFIX}{secrets.token_hex(4)}"
    user = User(username=username, email=f"{username}@example.com", phone="0300 0000000", **extra)
    user.set_unusable_password()
    user.save()
    return user


def _copy_order(order, *, user, owner, items, product_map=None):
    """Copy `order` (with the given items) into `owner`'s sandbox."""
    product_map = product_map or {}
    payment = Payment.all_objects.filter(order=order).first()
    created_at = order.created_at
    copy = Order.all_objects.get(pk=order.pk)
    copy.pk = copy.id = None
    copy._state.adding = True
    copy.user = user
    copy.owner_visitor = owner
    if user is not None:
        copy.full_name = user.get_full_name() or copy.full_name
        copy.email = user.email
    copy.total_amount = sum((i.price * i.quantity for i in items), Decimal("0"))
    copy.save()
    Order.all_objects.filter(pk=copy.pk).update(created_at=created_at)
    OrderItem.objects.bulk_create([
        OrderItem(order=copy, product_id=product_map.get(i.product_id, i.product_id),
                  color=i.color, size=i.size, price=i.price, quantity=i.quantity)
        for i in items
    ])
    if payment:
        Payment.objects.create(order=copy, card_number=payment.card_number, expiry=payment.expiry,
                               cvv="", payment_status=payment.payment_status)
    return copy


def create_visitor_customer():
    template = User.objects.filter(username=TEMPLATE_CUSTOMER).first()
    user = _new_user(first_name="Demo", last_name="Visitor",
                     address=getattr(template, "address", "") or "House 12, Street 4, Lahore")
    if template:
        for order in Order.all_objects.filter(user=template, owner_visitor=None).order_by("created_at"):
            _copy_order(order, user=user, owner=user, items=list(OrderItem.all_objects.filter(order=order)))
    return user


def create_visitor_vendor():
    template = Vendor.all_objects.filter(user__username=TEMPLATE_VENDOR).first()
    if template is None:
        raise Http404("Demo store not loaded")
    user = _new_user(first_name="Demo", last_name="Seller", is_vendor=True, is_customer=False)
    suffix = user.username[len(VISITOR_PREFIX):]

    store = Vendor.all_objects.get(pk=template.pk)
    store.pk = store.id = None
    store._state.adding = True
    store.user = user
    store.business_name = "My Demo Store"
    store.vendor_slug = f"my-demo-store-{suffix}"
    store.save()

    product_map = {}
    for product in Product.all_objects.filter(vendor=template).order_by("id"):
        old_id = product.pk
        colors = list(ProductColorVariant.objects.filter(product_id=old_id))
        sizes = list(ProductSizeVariant.objects.filter(product_id=old_id))
        product.pk = product.id = None
        product._state.adding = True
        product.vendor = store
        product.created_by = user
        product.slug = f"{product.slug[:240]}-{suffix}"
        product.save()
        product_map[old_id] = product.pk
        for variant in colors + sizes:
            variant.pk = variant.id = None
            variant._state.adding = True
            variant.product = product
            variant.save()

    # Copy the template store's orders (only its own items) so the dashboard,
    # orders and earnings pages have real-looking data to work with.
    orders = Order.all_objects.filter(owner_visitor=None, items__product__vendor=template).distinct()
    for order in orders.order_by("created_at"):
        items = list(OrderItem.all_objects.filter(order=order, product__vendor=template))
        _copy_order(order, user=order.user, owner=user, items=items, product_map=product_map)

    for w in Withdrawal.all_objects.filter(vendor=template):
        Withdrawal.objects.create(vendor=store, amount=w.amount, status=w.status)
    return user


def _rate_limited(request):
    key = f"demo-visitors:{client_ip(request)}"
    if cache.get(key, 0) >= MAX_VISITORS_PER_IP_PER_HOUR:
        return True
    if not cache.add(key, 1, 3600):
        cache.incr(key)
    return False


def _start(request, factory, welcome, next_url):
    if not settings.DEMO_MODE:
        raise Http404
    if _rate_limited(request):
        messages.warning(request, "Too many demo accounts from your network. Please try again later.")
        return redirect("login")

    guest_session_key = request.session.session_key
    with transaction.atomic():
        user = factory()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    guest_cart = (
        Cart.objects.filter(session_key=guest_session_key, user=None).first()
        if guest_session_key else None
    )
    if guest_cart:
        Cart.for_user(user).merge_with(guest_cart)
    messages.success(request, welcome)
    return redirect(next_url)


@require_POST
def demo_customer_login(request):
    return _start(request, create_visitor_customer,
                  "Welcome! This is your own private demo account. Shop freely.",
                  "customer_dashboard")


@require_POST
def demo_vendor_login(request):
    return _start(request, create_visitor_vendor,
                  "Welcome! This is your own private copy of the store: add, edit or delete "
                  "products and manage orders. Nobody else sees your changes.",
                  "vendor_dashboard")
