from django.conf import settings


def site_info(request):
    return {
        'admin_name': settings.ADMIN_NAME,
        'admin_phone': settings.ADMIN_PHONE,
        'admin_whatsapp': settings.ADMIN_WHATSAPP,
        'admin_email': settings.ADMIN_EMAIL,
        'demo_mode': settings.DEMO_MODE,
        'site_tagline': settings.SITE_TAGLINE,
    }
