"""
URL configuration for rsvp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny

api_urls = [
    # swagger docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="redoc",
    ),
    path("user-info/", include("user_profiles.api.urls")),
    path("auth/", include("registration.api.urls")),
    path("events/", include("events.api.urls")),
    path("payments/", include("payments.api.urls")),
    path("qr/", include("qr_codes.api.urls")),
    path("analytics/", include("analytics.api.urls")),
    path("communication/", include("communication.api.urls")),
    path("support/", include("support.api.urls")),
]

urlpatterns = [
    path("api/", include(api_urls)),
    path("admin/", admin.site.urls),

    path("", include("events.urls")),
    path("checkout/", include("payments.urls")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)