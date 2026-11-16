"""Per-visitor sandboxes for the public demo (DEMO_MODE only).

Demo visitors get their own throw-away accounts (usernames start with
"visitor_"). Everything a visitor creates - their private store, its
products, their orders - is hidden from every other visitor, so two people
using the demo at the same time never see each other's changes.

The current user is stored in a context variable by SandboxMiddleware, and
the default managers below filter on it. Outside DEMO_MODE nothing is
filtered.
"""
from contextvars import ContextVar

from django.conf import settings
from django.db import models
from django.db.models import Q

VISITOR_PREFIX = "visitor_"
current_user_id = ContextVar("markethub_current_user_id", default=None)


def active():
    return getattr(settings, "DEMO_MODE", False)


def _visible(user_path):
    """Q() keeping rows not owned by a visitor, or owned by the current user."""
    lookup = {f"{user_path}__username__startswith": VISITOR_PREFIX}
    q = ~Q(**lookup) | Q(**{f"{user_path}__isnull": True})
    uid = current_user_id.get()
    if uid is not None:
        q |= Q(**{f"{user_path}_id": uid}) if "__" not in user_path else Q(**{f"{user_path}__id": uid})
    return q


class _SandboxManager(models.Manager):
    """Default manager that hides other visitors' sandbox rows in DEMO_MODE.

    `user_path` is a class attribute (not an __init__ argument) because Django
    builds related managers by subclassing the default manager and calling
    __init__() with no arguments.
    """

    user_path = None

    def deconstruct(self):
        # Keep migrations free of this manager.
        return (False, "django.db.models.Manager", None, (), {})

    def get_queryset(self):
        qs = super().get_queryset()
        if not active():
            return qs
        return qs.filter(_visible(self.user_path))


class SandboxMiddleware:
    """Remember who is making the request (must come after AuthenticationMiddleware)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = current_user_id.set(user.pk if user is not None and user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            current_user_id.reset(token)


def SandboxManager(user_path):
    """Manager for a model whose owning user is reached through `user_path`."""
    cls = type(f"SandboxManager_{user_path}", (_SandboxManager,), {"user_path": user_path})
    return cls()
