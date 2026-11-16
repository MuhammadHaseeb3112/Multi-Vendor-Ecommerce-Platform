

from datetime import datetime

from django.conf import settings

from .models import Cart, Category


def add_year(request):
    return {'year': datetime.now().year}

def cart_total_items(request):
    cart = Cart.get_or_create_cart(request)
    return {'cart': cart}



def demo(request):
    """Expose demo-mode details (shared logins shown on the login page)."""
    if not settings.DEMO_MODE:
        return {"DEMO_MODE": False}
    return {
        "DEMO_MODE": True,
        "demo_password": settings.DEMO_PASSWORD,
        # Customer and Vendor get private accounts (api/demoviews.py);
        # Admin is a shared, read-only view of the whole marketplace.
        "demo_accounts": [
            ("Admin", "demo_admin"),
        ],
    }


def categories(request):
    return {
        "categories": Category.objects.all()
    }
