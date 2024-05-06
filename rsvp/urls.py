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
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # administration
    path('admin/', admin.site.urls),

    # swagger docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('api/user-info/', include('user_profiles.api.urls')),
    path('api/auth/', include('registration.api.urls')),
    
    path('api/events/', include('events.api.urls')),
    path('api/payments/', include('payments.api.urls')),
    path('api/qr/', include('qr_codes.api.urls')),
    path('api/analytics/', include('analytics.api.urls')),
    path('api/communication/', include('communication.api.urls')),
    path('api/support/', include('support.api.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)