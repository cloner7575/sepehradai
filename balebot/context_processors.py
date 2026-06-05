from django.db.utils import OperationalError

from balebot.models import BotSettings
from balebot.platform import all_platforms, get_active_platform, platform_label
from balebot.workspace import get_workspace_for_user


def panel_branding(request):
    try:
        active = get_active_platform(request)
        ws = get_workspace_for_user(request.user) if request.user.is_authenticated else None
        branding = None
        if ws and ws.is_active:
            branding = BotSettings.get_for_platform(ws, active)
        return {
            'bot_branding': branding,
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
