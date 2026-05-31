from django.db.utils import OperationalError

from balebot.platform import all_platforms, get_active_platform, get_bot_settings_for_request, platform_label


def panel_branding(request):
    try:
        active = get_active_platform(request)
        return {
            'bot_branding': get_bot_settings_for_request(request),
            'active_platform': active,
            'active_platform_label': platform_label(active),
            'available_platforms': all_platforms(),
        }
    except OperationalError:
        return {
            'bot_branding': None,
            'active_platform': 'bale',
            'active_platform_label': 'بله',
            'available_platforms': all_platforms(),
        }
