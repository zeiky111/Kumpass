import re

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.conf import settings
from django.views.static import serve as serve_static


def root_home(request):
    return JsonResponse(
        {
            "message": "Kumpas backend is running",
            "available_routes": [
                "/admin/",
                "/api/health/",
                "/api/auth/signup/",
                "/api/auth/login/",
                "/api/learning/state/",
                "/api/sign/predict/",
                "/api/sign/recent/",
            ],
        }
    )

urlpatterns = [
    path("", root_home),
    path("admin/", admin.site.urls),
    path("api/", include("signtext.urls")),
]

# Serve user-uploaded media files. django.conf.urls.static.static() no-ops
# whenever DEBUG=False, and this deployment has no separate web server (nginx/
# S3/CDN) in front of it, so without an explicit route here the /media/...
# URLs handed out by ModuleFileSerializer 404 for everyone in production,
# including students trying to open files teachers uploaded.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve_static,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
