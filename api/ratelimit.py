"""Simple login throttling (brute-force protection).

Failed logins are counted in the Django cache per IP + username and per IP.
After too many failures the login form is locked for a while. The cache is a
database cache by default, so the limit is shared by all Gunicorn workers.
"""
from django.conf import settings
from django.core.cache import cache

MAX_PER_ACCOUNT = getattr(settings, "LOGIN_MAX_FAILURES", 5)
MAX_PER_IP = getattr(settings, "LOGIN_MAX_FAILURES_PER_IP", 20)
LOCKOUT_SECONDS = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 15 * 60)


def client_ip(request):
    """Visitor IP. Behind our own reverse proxy (TRUSTED_PROXY=True) REMOTE_ADDR
    is the proxy, so use the address the proxy appended to X-Forwarded-For."""
    if getattr(settings, "TRUSTED_PROXY", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _keys(request, identifier):
    ip = client_ip(request)
    ident = (identifier or "").strip().lower()
    return f"login-fail:{ip}:{ident}", f"login-fail-ip:{ip}"


def is_locked(request, identifier):
    account_key, ip_key = _keys(request, identifier)
    return (
        cache.get(account_key, 0) >= MAX_PER_ACCOUNT
        or cache.get(ip_key, 0) >= MAX_PER_IP
    )


def register_failure(request, identifier):
    for key in _keys(request, identifier):
        if cache.add(key, 1, LOCKOUT_SECONDS):
            continue
        try:
            cache.incr(key)
        except ValueError:  # expired between add() and incr()
            cache.set(key, 1, LOCKOUT_SECONDS)


def reset(request, identifier):
    cache.delete(_keys(request, identifier)[0])
