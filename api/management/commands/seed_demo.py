"""Load a clean demo data set (no real customer data).

    python manage.py seed_demo            # only if the database is empty
    python manage.py seed_demo --reset    # wipe everything and reload

Creates three demo accounts (customer, vendor, admin) that share
DEMO_PASSWORD, five stores, the product catalogue from api/demo/catalog.json
and about a month of sample orders so every dashboard has something to show.
"""
import json
import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import (
    Category, Coupon, Order, OrderItem, Payment, Product, ProductColorVariant,
    ProductSizeVariant, Review, Vendor, Withdrawal,
)

User = get_user_model()
CATALOG = Path(__file__).resolve().parents[2] / "demo" / "catalog.json"
DOCUMENT = "vendor/licenses/demo-document.pdf"

CUSTOMERS = [
    ("demo_customer", "Demo", "Customer", "Lahore"),
    ("ayesha.k", "Ayesha", "Khan", "Karachi"),
    ("bilal.r", "Bilal", "Raza", "Islamabad"),
    ("sana.m", "Sana", "Malik", "Multan"),
    ("omar.f", "Omar", "Farooq", "Faisalabad"),
]
REVIEWS = [
    (5, "Exactly as described and delivered on time."),
    (4, "Good quality for the price. Packaging could be better."),
    (5, "Second order from this store, very happy."),
    (3, "Works fine, delivery took a few extra days."),
    (4, "Looks great. Would recommend."),
]
# status -> share of orders
STATUSES = [("Delivered", 12), ("Shipped", 5), ("Processing", 4), ("Pending", 6), ("Cancelled", 3)]


class Command(BaseCommand):
    help = "Load demo data: demo accounts, stores, products and sample orders."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete ALL existing data first.")
        parser.add_argument("--force", action="store_true", help="Allow running when DEMO_MODE is off.")

    def handle(self, *args, **opts):
        if not (settings.DEMO_MODE or opts["force"]):
            raise CommandError("DEMO_MODE is off. Use --force if you really want demo data here.")

        if opts["reset"]:
            call_command("flush", interactive=False, verbosity=0)
        elif User.objects.exists() or Product.objects.exists():
            self.stdout.write("Database already has data; nothing to do (use --reset to reload).")
            return

        with transaction.atomic():
            self.rng = random.Random(2026)
            data = json.loads(CATALOG.read_text(encoding="utf-8"))
            self.make_accounts()
            vendors = self.make_vendors(data["vendors"])
            products = self.make_catalog(data, vendors)
            self.make_coupons()
            self.make_orders(products)
            self.make_reviews(products)
            self.make_withdrawals(vendors)

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded: {len(products)} products, {Order.objects.count()} orders. "
            "Logins: demo_customer / demo_vendor / demo_admin."
        ))

    # ------------------------------------------------------------------ users
    def make_user(self, username, first="", last="", **extra):
        user = User(username=username, first_name=first, last_name=last,
                    email=f"{username}@example.com", **extra)
        if username.startswith("demo_"):
            user.set_password(settings.DEMO_PASSWORD)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def make_accounts(self):
        self.make_user("demo_admin", "Demo", "Admin", is_staff=True, is_superuser=True)
        self.customers = [
            self.make_user(username, first, last, address=f"House 12, Street 4, {city}",
                           phone="0300 0000000")
            for username, first, last, city in CUSTOMERS
        ]
        self.cities = {c[0]: c[3] for c in CUSTOMERS}

    # ---------------------------------------------------------------- vendors
    def make_vendors(self, rows):
        if not default_storage.exists(DOCUMENT):
            default_storage.save(DOCUMENT, ContentFile(b"%PDF-1.4\n% MarketHub demo document\n%%EOF\n"))
        vendors = {}
        for i, row in enumerate(rows, start=1):
            owner = self.make_user(row["username"], row["business_name"], "", is_vendor=True)
            vendors[row["key"]] = Vendor.objects.create(
                user=owner, business_name=row["business_name"], vendor_slug=row["slug"],
                business_type="Company", registration_number=f"DEMO-REG-{1000 + i}",
                business_description=row["desc"], phone_number="0300 0000000",
                address="Demo Plaza, Main Boulevard", city=row["city"], state="Punjab",
                zip_code="54000", country="Pakistan", bank_name="Demo Bank",
                account_holder_name=row["business_name"], account_number=f"DEMO-{i:04d}",
                swift_code="DEMOPKKA", business_license=DOCUMENT, id_proof=DOCUMENT,
                logo=row["logo"] or None, verified_vendor=True, is_payment_info_verified=True,
                preferred_payment_method="Bank Transfer", agreed_to_terms=True,
                average_rating=round(self.rng.uniform(4.2, 4.9), 1),
                total_reviews=self.rng.randint(40, 400),
            )
        return vendors

    # ---------------------------------------------------------------- catalog
    def make_catalog(self, data, vendors):
        categories = {
            row["slug"]: Category.objects.create(name=row["name"], slug=row["slug"], image=row["image"])
            for row in data["categories"]
        }
        products = []
        for row in data["products"]:
            vendor = vendors[row["vendor"]]
            product = Product.objects.create(
                name=row["name"], slug=row["slug"], category=categories[row["category"]],
                vendor=vendor, created_by=vendor.user, short_details=row["short_details"],
                description=row["description"], brand=row["brand"],
                base_price=Decimal(row["base_price"]), stock=row["stock"], image=row["image"],
                is_available=row["is_available"], tags=row["tags"],
            )
            for color in row["colors"]:
                ProductColorVariant.objects.create(product=product, **{**color, "price": Decimal(color["price"])})
            for size in row["sizes"]:
                ProductSizeVariant.objects.create(product=product, **{**size, "price": Decimal(size["price"])})
            products.append(product)
        return products

    def make_coupons(self):
        now = timezone.now()
        Coupon.objects.create(code="WELCOME10", discount=10, discount_type="percentage", active=True,
                              valid_from=now - timedelta(days=30), valid_to=now + timedelta(days=365))
        Coupon.objects.create(code="SAVE500", discount=500, discount_type="fixed", active=True,
                              min_cart_amount=5000, valid_from=now - timedelta(days=30),
                              valid_to=now + timedelta(days=365))
        Coupon.objects.create(code="EID2025", discount=20, discount_type="percentage", active=False,
                              valid_from=now - timedelta(days=200), valid_to=now - timedelta(days=170))

    # ----------------------------------------------------------------- orders
    def make_orders(self, products):
        rng, now = self.rng, timezone.now()
        affordable = [p for p in products if p.base_price < 60000]
        statuses = [s for s, n in STATUSES for _ in range(n)]
        rng.shuffle(statuses)
        for n, status in enumerate(statuses):
            # every third order belongs to the demo customer
            customer = self.customers[0] if n % 3 == 0 else rng.choice(self.customers[1:])
            created = now - timedelta(days=rng.randint(1, 45), hours=rng.randint(0, 23))
            if status in ("Pending", "Processing"):
                created = now - timedelta(days=rng.randint(0, 4), hours=rng.randint(1, 20))
            order = Order.objects.create(
                user=customer, full_name=customer.get_full_name(), email=customer.email,
                phone="0300 0000000", address=customer.address,
                city=self.cities[customer.username], zip_code="54000",
                total_amount=0, status=status,
            )
            total = Decimal("0")
            for product in rng.sample(affordable, rng.randint(1, 3)):
                quantity = rng.randint(1, 2)
                OrderItem.objects.create(order=order, product=product, price=product.base_price,
                                         quantity=quantity)
                total += product.base_price * quantity
            extra = {}
            if status in ("Shipped", "Delivered"):
                extra = dict(shipped_at=created + timedelta(days=1), courier=rng.choice(["TCS", "Leopards", "M&P"]),
                             tracking_number=f"DEMO{rng.randint(10**7, 10**8 - 1)}",
                             estimated_delivery=(created + timedelta(days=4)).date())
            if status == "Delivered":
                extra["delivered_at"] = created + timedelta(days=rng.randint(2, 4))
            Order.objects.filter(pk=order.pk).update(total_amount=total, created_at=created, **extra)
            Payment.objects.create(order=order, card_number=f"************{rng.randint(1000, 9999)}",
                                   expiry="12/30", payment_status="Success")

    def make_reviews(self, products):
        for product in self.rng.sample(products, 14):
            for reviewer in self.rng.sample(self.customers, self.rng.randint(1, 3)):
                rating, comment = self.rng.choice(REVIEWS)
                Review.objects.create(product=product, user=reviewer, rating=rating, comment=comment)

    def make_withdrawals(self, vendors):
        for vendor in vendors.values():
            earned = sum(
                (item.price * item.quantity for item in
                 OrderItem.objects.filter(product__vendor=vendor, order__status="Delivered")),
                Decimal("0"),
            )
            paid = (earned * Decimal("0.4")).quantize(Decimal("1")) if earned else Decimal("0")
            if paid:
                Withdrawal.objects.create(vendor=vendor, amount=paid, status="Approved")
            vendor.total_earnings = earned
            vendor.available_balance = earned - paid
            vendor.save(update_fields=["total_earnings", "available_balance"])
        demo = vendors["chm"]
        if demo.available_balance > 2000:
            Withdrawal.objects.create(vendor=demo, amount=Decimal("2000"), status="Pending")
