from django.conf import settings


def landing_settings(request):
    return {
        'LANDING_DEMO_BOT_URL': getattr(settings, 'LANDING_DEMO_BOT_URL', ''),
    }
