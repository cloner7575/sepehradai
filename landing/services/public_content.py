from django.conf import settings as django_settings

from landing.models import LandingSettings, ShowcaseBot, SubscriptionPlan
from landing.services.business_categories import landing_chip_names, other_category_label


def get_public_landing_context() -> dict:
    settings_obj = LandingSettings.get_solo()
    plans = list(SubscriptionPlan.objects.filter(is_active=True))
    active_bots = list(ShowcaseBot.objects.filter(is_active=True))
    landing_bots = [bot for bot in active_bots if bot.show_on_landing]
    return {
        'landing_settings': settings_obj,
        'LANDING_DEMO_BOT_URL': settings_obj.resolved_demo_bot_url(),
        'subscription_plans': plans,
        'business_categories': landing_chip_names(),
        'other_category_label': other_category_label(),
        'showcase_bots': landing_bots,
        'showcase_bots_total': len(active_bots),
    }


def get_showcase_bots_context() -> dict:
    settings_obj = LandingSettings.get_solo()
    bots = list(ShowcaseBot.objects.filter(is_active=True))
    return {
        'landing_settings': settings_obj,
        'LANDING_DEMO_BOT_URL': settings_obj.resolved_demo_bot_url(),
        'showcase_bots': bots,
    }


def default_demo_bot_url() -> str:
    try:
        return LandingSettings.get_solo().resolved_demo_bot_url()
    except Exception:
        return getattr(django_settings, 'LANDING_DEMO_BOT_URL', '').strip()
