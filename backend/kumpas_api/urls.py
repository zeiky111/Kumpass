from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


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

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
