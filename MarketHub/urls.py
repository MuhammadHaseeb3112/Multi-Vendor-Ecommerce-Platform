import os
from django.urls import re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('api.urls')),
]

# The public demo exposes a shared admin login, so Django's own admin site
# (which could edit users and passwords) is switched off there.
if not settings.DEMO_MODE:
    urlpatterns.insert(0, path('admin/', admin.site.urls))

# Uploaded media: served by Django in development, or when SERVE_MEDIA=True
# (small single-container deployments without a separate web server).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif os.getenv("SERVE_MEDIA", "False") == "True":
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]