from django.conf import settings as django_settings

from landing.models import LandingSettings, SubscriptionPlan


def get_public_landing_context() -> dict:
    settings_obj = LandingSettings.get_solo()
    plans = list(SubscriptionPlan.objects.filter(is_active=True))
    return {
        'landing_settings': settings_obj,
        'LANDING_DEMO_BOT_URL': settings_obj.resolved_demo_bot_url(),
        'subscription_plans': plans,
    }


def default_demo_bot_url() -> str:
    try:
        return LandingSettings.get_solo().resolved_demo_bot_url()
    except Exception:
        return getattr(django_settings, 'LANDING_DEMO_BOT_URL', '').strip()
