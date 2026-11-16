from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Cart, Category, Coupon, Order, OrderItem, Payment, Product, Vendor

User = get_user_model()

# 1x1 transparent GIF, enough for ImageField in tests.
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
    b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def image(name="img.gif"):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


def make_vendor(username):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass12345", is_vendor=True)
    vendor = Vendor.objects.create(
        user=user, business_name=f"{username} Store", business_type="Retail",
        registration_number="R1", phone_number="03000000000", address="Street 1",
        city="Lahore", state="Punjab", zip_code="54000", country="Pakistan",
        bank_name="Bank", account_holder_name=username, account_number="0001",
        swift_code="SWFT", business_license="vendor/licenses/x.pdf", id_proof="vendor/id_proof/x.pdf",
    )
    return user, vendor


@override_settings(MEDIA_ROOT="/tmp/markethub-test-media")
class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Electronics", image=image())
        cls.vendor_user, cls.vendor = make_vendor("vendor1")
        cls.other_vendor_user, cls.other_vendor = make_vendor("vendor2")
        cls.product = Product.objects.create(
            name="Test Product", category=cls.category, short_details="s", description="d",
            base_price=Decimal("100.00"), stock=5, image=image(), is_available=True, vendor=cls.vendor,
        )
        cls.customer = User.objects.create_user(username="alice", email="alice@example.com", password="pass12345")
        cls.order = Order.objects.create(
            user=cls.customer, full_name="Alice", email="alice@example.com", phone="03001234567",
            address="Street", city="Lahore", zip_code="54000", total_amount=Decimal("200.00"), status="Pending",
        )
        OrderItem.objects.create(order=cls.order, product=cls.product, price=Decimal("100.00"), quantity=2)


class CouponTestCase(BaseTestCase):
    def setUp(self):
        self.cart = Cart.objects.create(user=self.customer)
        self.cart.items.create(product=self.product, quantity=2)
        self.valid_coupon = Coupon.objects.create(
            code="DISCOUNT10", discount=10, active=True,
            valid_from=timezone.now() - timezone.timedelta(days=1),
            valid_to=timezone.now() + timezone.timedelta(days=1),
        )

    def test_coupon_application(self):
        self.cart.coupon = self.valid_coupon
        self.cart.update_totals()
        self.assertAlmostEqual(float(self.cart.total_amount()), 180.0)  # 200 - 10%

    def test_coupon_not_yet_valid(self):
        self.valid_coupon.valid_from = timezone.now() + timezone.timedelta(days=1)
        self.valid_coupon.save()
        self.assertTrue(self.valid_coupon.valid_from > timezone.now())


class TrackOrderTests(BaseTestCase):
    url = "/track-order/"

    def test_order_id_alone_does_not_reveal_order(self):
        resp = self.client.post(self.url, {"query": self.order.id})
        self.assertIsNone(resp.context["order"])

    def test_email_alone_does_not_reveal_order(self):
        resp = self.client.post(self.url, {"query": "alice@example.com"})
        self.assertIsNone(resp.context["order"])

    def test_order_id_with_matching_email(self):
        resp = self.client.post(self.url, {"query": self.order.id, "email": "ALICE@example.com"})
        self.assertEqual(resp.context["order"], self.order)

    def test_owner_can_track_without_email(self):
        self.client.force_login(self.customer)
        resp = self.client.post(self.url, {"query": self.order.id})
        self.assertEqual(resp.context["order"], self.order)


class AccessControlTests(BaseTestCase):
    def test_anonymous_cannot_delete_customer(self):
        resp = self.client.post(reverse("customer_delete", args=[self.customer.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_customer_cannot_open_admin_withdrawals(self):
        self.client.force_login(self.customer)
        resp = self.client.get(reverse("admin_vendor_withdrawals"))
        self.assertEqual(resp.status_code, 302)

    def test_delete_product_rejects_get(self):
        self.client.force_login(self.vendor_user)
        resp = self.client.get(reverse("delete_product", args=[self.product.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_other_vendor_cannot_see_order(self):
        self.client.force_login(self.other_vendor_user)
        resp = self.client.get(reverse("vendor_order_detail", args=[self.order.id]))
        self.assertEqual(resp.status_code, 404)

    def test_receipt_only_for_owner(self):
        self.client.force_login(self.other_vendor_user)
        resp = self.client.get(reverse("generate_receipt", args=[self.order.id]))
        self.assertEqual(resp.status_code, 404)


class VendorAreaTests(BaseTestCase):
    def test_customer_opening_vendor_pages_is_redirected(self):
        self.client.force_login(self.customer)
        for name in ["vendor_earnings", "vendor_manage_orders", "vendor_dashboard"]:
            with self.subTest(page=name):
                self.assertIn(self.client.get(reverse(name)).status_code, (302, 403, 404))


class VendorStockTests(BaseTestCase):
    def test_mark_processing_decrements_stock(self):
        self.client.force_login(self.vendor_user)
        self.client.post(reverse("vendor_order_detail", args=[self.order.id]), {"action": "mark_processing"})
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.order.status, "Processing")

    def test_insufficient_stock_keeps_order_pending(self):
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        self.client.force_login(self.vendor_user)
        self.client.post(reverse("vendor_order_detail", args=[self.order.id]), {"action": "mark_processing"})
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(self.order.status, "Pending")


class PaymentStorageTests(BaseTestCase):
    def test_update_payment_never_stores_full_card_or_cvv(self):
        Payment.objects.create(order=self.order, card_number="************1111", expiry="12/30")
        self.client.force_login(self.customer)
        self.client.post(reverse("update_payment_method"), {
            "card_number": "4242 4242 4242 4242", "expiry": "12/30", "cvv": "123",
        })
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.card_number, "************4242")
        self.assertEqual(payment.cvv, "")


class PublicPagesTests(TestCase):
    def test_home_page_works_on_empty_database(self):
        self.assertEqual(self.client.get("/").status_code, 200)


class DuplicateCartTests(BaseTestCase):
    def test_duplicate_carts_are_merged(self):
        Cart.objects.create(user=self.customer)
        b = Cart.objects.create(user=self.customer)
        b.items.create(product=self.product, quantity=1)
        Cart.objects.create(user=self.customer)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(Cart.objects.filter(user=self.customer).count(), 1)
        self.assertEqual(Cart.for_user(self.customer).items.count(), 1)


class GuestCartTests(TestCase):
    def test_guest_can_remove_coupon(self):
        self.client.get("/")
        resp = self.client.get(reverse("remove_coupon"))
        self.assertEqual(resp.status_code, 302)


class LoginRateLimitTests(BaseTestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_locks_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "pass12345"})
        self.assertEqual(resp.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_successful_login_works(self):
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "pass12345"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_by_email(self):
        self.client.post(reverse("login"), {"username": "ALICE@example.com", "password": "pass12345"})
        self.assertIn("_auth_user_id", self.client.session)


class CartFlowTests(BaseTestCase):
    def test_guest_add_to_cart_then_login_keeps_items(self):
        self.client.get("/")
        self.client.post(reverse("add_to_cart"), {"product_id": self.product.id, "quantity": 2})
        self.client.post(reverse("login"), {"username": "alice", "password": "pass12345"})
        cart = Cart.for_user(self.customer)
        self.assertEqual(cart.items.get().quantity, 2)

    def test_add_to_cart_requires_post(self):
        self.assertEqual(self.client.get(reverse("add_to_cart")).status_code, 405)

    def test_add_to_cart_with_product_in_url(self):
        self.client.get("/")
        resp = self.client.post(reverse("add_to_cart", args=[self.product.id]), {"quantity": 1})
        self.assertEqual(resp.status_code, 302)


class RoutingTests(BaseTestCase):
    def test_vendor_routes_not_shadowed_by_store_slug(self):
        self.assertEqual(reverse("register_vendor"), "/vendor/register/")
        self.client.force_login(self.vendor_user)
        resp = self.client.get(reverse("vendor_track_order_view"))
        self.assertEqual(resp.status_code, 200)

    def test_public_pages(self):
        for name in ["home", "shop", "about_us", "contact", "track_order", "login", "register_customer", "register_vendor"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


@override_settings(DEMO_MODE=True, MEDIA_ROOT="/tmp/markethub-test-media")
class DemoModeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0)

    def test_seed_creates_demo_accounts_and_data(self):
        self.assertEqual(Product.objects.count(), 26)
        self.assertEqual(Order.objects.count(), 30)
        self.assertTrue(User.objects.get(username="demo_admin").is_superuser)
        self.assertTrue(hasattr(User.objects.get(username="demo_vendor"), "vendor"))
        # no real addresses: every account uses example.com
        self.assertFalse(User.objects.exclude(email__endswith="@example.com").exists())

    def test_seed_is_idempotent(self):
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Order.objects.count(), 30)

    def test_demo_logins_work_and_dashboards_render(self):
        for username, page in [("demo_customer", "customer_dashboard"),
                               ("demo_vendor", "vendor_dashboard"),
                               ("demo_admin", "admin_dashboard")]:
            with self.subTest(user=username):
                self.assertTrue(self.client.login(username=username, password="DemoPass123!"))
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)
                self.client.logout()

    def test_login_page_shows_demo_accounts(self):
        resp = self.client.get(reverse("login"))
        self.assertContains(resp, reverse("demo_customer_login"))
        self.assertContains(resp, reverse("demo_vendor_login"))
        self.assertContains(resp, "demo_admin")

    def test_password_change_is_blocked(self):
        self.client.login(username="demo_customer", password="DemoPass123!")
        self.client.post(reverse("change_password"), {
            "old_password": "DemoPass123!", "new_password1": "Hacked12345!", "new_password2": "Hacked12345!",
        })
        self.assertTrue(User.objects.get(username="demo_customer").check_password("DemoPass123!"))

    def test_customer_button_creates_private_account(self):
        from django.core.cache import cache
        cache.clear()
        template_orders = Order.objects.filter(user__username="demo_customer").count()
        resp = self.client.post(reverse("demo_customer_login"))
        self.assertRedirects(resp, reverse("customer_dashboard"))
        visitor = User.objects.get(pk=self.client.session["_auth_user_id"])
        self.assertTrue(visitor.username.startswith("visitor_"))
        self.assertEqual(Order.all_objects.filter(user=visitor).count(), template_orders)
        # a second visitor gets a different account
        other = self.client_class()
        other.post(reverse("demo_customer_login"))
        self.assertNotEqual(other.session["_auth_user_id"], self.client.session["_auth_user_id"])

    def test_visitor_can_shop(self):
        from django.core.cache import cache
        cache.clear()
        self.client.post(reverse("demo_customer_login"))
        product = Product.objects.filter(base_price__lt=60000).first()
        self.client.post(reverse("add_to_cart"), {"product_id": product.id, "quantity": 1})
        visitor = User.objects.get(pk=self.client.session["_auth_user_id"])
        self.assertEqual(Cart.for_user(visitor).items.count(), 1)

    def test_vendor_button_creates_private_store(self):
        from django.core.cache import cache
        cache.clear()
        public_before = Product.objects.count()
        resp = self.client.post(reverse("demo_vendor_login"))
        self.assertRedirects(resp, reverse("vendor_dashboard"))
        visitor = User.objects.get(pk=self.client.session["_auth_user_id"])
        store = Vendor.all_objects.get(user=visitor)
        own = Product.all_objects.filter(vendor=store)
        template_count = Product.all_objects.filter(vendor__user__username="demo_vendor").count()
        self.assertEqual(own.count(), template_count)
        self.assertTrue(OrderItem.all_objects.filter(product__vendor=store).exists())
        # The visitor can manage their own store...
        self.assertEqual(self.client.get(reverse("vendor_dashboard")).status_code, 200)
        product = own.first()
        self.client.post(reverse("delete_product", args=[product.pk]))
        self.assertFalse(Product.all_objects.filter(pk=product.pk).exists())
        # ...and nobody else sees it.
        other = self.client_class()
        self.assertEqual(other.get(reverse("shop")).status_code, 200)
        from api import sandbox
        token = sandbox.current_user_id.set(None)
        try:
            self.assertEqual(Product.objects.count(), public_before)
            self.assertFalse(Order.objects.filter(owner_visitor=visitor).exists())
        finally:
            sandbox.current_user_id.reset(token)
        resp = other.get(reverse("vendor_detail", args=[store.vendor_slug]))
        self.assertNotContains(resp, own.first().name, status_code=resp.status_code)

    def test_visitor_orders_hidden_from_shared_vendor(self):
        from django.core.cache import cache
        cache.clear()
        self.client.post(reverse("demo_customer_login"))
        visitor = User.objects.get(pk=self.client.session["_auth_user_id"])
        from api import sandbox
        token = sandbox.current_user_id.set(User.objects.get(username="demo_vendor").pk)
        try:
            self.assertFalse(Order.objects.filter(user=visitor).exists())
        finally:
            sandbox.current_user_id.reset(token)

    def test_shared_vendor_is_read_only(self):
        self.client.login(username="demo_vendor", password="DemoPass123!")
        product = Product.objects.filter(vendor__user__username="demo_vendor").first()
        self.client.post(reverse("delete_product", args=[product.pk]))
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_shared_admin_is_read_only(self):
        self.client.login(username="demo_admin", password="DemoPass123!")
        coupon = Coupon.objects.first()
        self.client.post(reverse("admin-coupon-delete", args=[coupon.pk]))
        self.assertTrue(Coupon.objects.filter(pk=coupon.pk).exists())

    def test_reviews_and_signups_are_off(self):
        from django.core.cache import cache
        cache.clear()
        self.client.post(reverse("register_customer"), {"username": "newbie", "email": "n@example.com",
                                                         "password1": "Xyz12345!a", "password2": "Xyz12345!a"})
        self.assertFalse(User.objects.filter(username="newbie").exists())
        self.client.post(reverse("demo_customer_login"))
        product = Product.objects.first()
        before = product.reviews.count()
        self.client.post(reverse("add_review", args=[product.slug]), {"rating": 1, "comment": "spam"})
        self.assertEqual(product.reviews.count(), before)

    def test_admin_cannot_delete_users_in_demo(self):
        self.client.login(username="demo_admin", password="DemoPass123!")
        target = User.objects.get(username="demo_customer")
        self.client.post(reverse("customer_delete", args=[target.pk]))
        self.assertTrue(User.objects.filter(pk=target.pk).exists())


class DemoModeOffTests(TestCase):
    def test_seed_refuses_outside_demo_mode(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("seed_demo", verbosity=0)

    def test_demo_customer_url_is_off(self):
        self.assertEqual(self.client.post(reverse("demo_customer_login")).status_code, 404)

    def test_login_page_has_no_demo_box(self):
        resp = self.client.get(reverse("login"))
        self.assertNotContains(resp, "demo_admin")
        self.assertNotContains(resp, "/demo/vendor/")
