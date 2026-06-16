from django.db.utils import OperationalError

from balebot.models import BotSettings
from balebot.platform import (
    allowed_platforms_for_workspace,
    get_active_platform,
    has_instagram_access_for_request,
    has_miniapp_access_for_request,
    platform_label,
)
from balebot.workspace import get_workspace_for_user


def panel_branding(request):
    try:
        ws = get_workspace_for_user(request.user) if request.user.is_authenticated else None
        active = get_active_platform(request, ws)
        branding = None
        if ws and ws.is_active and ws.has_platform_access(active):
            branding = BotSettings.get_for_platform(ws, active)
        return {
            'bot_branding': branding,
            'active_platform': active,
            'active_platform_label': platform_label(active),
            'available_platforms': allowed_platforms_for_workspace(ws),
            'panel_workspace': ws,
            'has_miniapp_access': has_miniapp_access_for_request(request, ws),
            'has_instagram_access': has_instagram_access_for_request(request, ws),
        }
    except OperationalError:
        return {
            'bot_branding': None,
            'active_platform': 'bale',
            'active_platform_label': 'بله',
            'available_platforms': allowed_platforms_for_workspace(None),
            'panel_workspace': None,
            'has_miniapp_access': False,
            'has_instagram_access': False,
        }
