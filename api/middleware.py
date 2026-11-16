from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from .models import Cart


class MediaCacheMiddleware:
    """Let browsers cache uploaded images (served by Django when SERVE_MEDIA=True)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/media/') and response.status_code == 200:
            response['Cache-Control'] = 'public, max-age=604800'
        return response


class VendorAreaMiddleware:
    """Vendor pages look up request.user.vendor; a customer or admin who opens
    one should get a friendly redirect, not a server error."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        from django.core.exceptions import ObjectDoesNotExist

        if request.path.startswith('/vendor/') and isinstance(exception, ObjectDoesNotExist):
            if 'vendor' in str(exception).lower():
                messages.info(request, "That page is for vendors. Sign in with a vendor account to see it.")
                return redirect('home')
        return None


class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Media/static files don't need a cart (and parallel image requests
        # used to create duplicate carts).
        if request.path.startswith(('/media/', '/static/')):
            return self.get_response(request)

        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.create()

        if request.user.is_authenticated:
            # Get or create cart for logged-in user
            cart = Cart.for_user(request.user)
        else:
            # Get or create cart for anonymous user by session key
            session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)

        # Attach the cart instance to the request object
        request.cart = cart

        # Continue processing request
        response = self.get_response(request)
        return response


class DemoGuardMiddleware:
    """Keeps the shared public demo clean for every visitor (DEMO_MODE only).

    - demo_customer, demo_vendor and demo_admin are shared logins, so they are
      read-only: every page opens, but nothing they submit is saved.
    - "Customer" on the login page creates a private visitor account
      (see api/demoviews.py), which can shop, check out and track orders.
    - Things every visitor would see (reviews, questions, sign-ups) and
      account/password changes are switched off for everyone.
    """

    SHARED_READ_ONLY = ('demo_customer', 'demo_vendor', 'demo_admin')
    ALWAYS_ALLOWED = ('/login/', '/logout/', '/demo/')
    LOCKED_FOR_ALL = (
        '/register/',
        '/vendor/register/',
        '/ask-question/',
        '/profile/change-password/',
        '/profile/edit/',
        '/password-reset/',
        '/reset/',
        '/admin-panel/customers/',
        '/admin-panel/vendors/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def blocked_reason(self, request):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return None
        path = request.path
        if path.startswith(self.ALWAYS_ALLOWED):
            return None
        if path.startswith(self.LOCKED_FOR_ALL) or path.endswith('/review/'):
            return "This action is turned off in the public demo."
        if request.user.is_authenticated and request.user.username in self.SHARED_READ_ONLY:
            return ("This shared demo account is read-only, so other visitors always see the "
                    "same data. Pick Customer or Vendor on the login page for your own account.")
        return None

    def __call__(self, request):
        if settings.DEMO_MODE:
            reason = self.blocked_reason(request)
            if reason:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'message': reason}, status=403)
                messages.warning(request, reason)
                return redirect(request.META.get('HTTP_REFERER') or 'home')
        return self.get_response(request)
