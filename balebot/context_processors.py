from django.db.utils import OperationalError

from balebot.models import BotSettings, InboundMessage
from balebot.platform import (
    allowed_platforms_for_workspace,
    get_active_platform,
    has_instagram_access_for_request,
    has_miniapp_access_for_request,
    platform_label,
)
from balebot.workspace import get_workspace_for_user


def _panel_module(request) -> str:
    if not request.resolver_match:
        return 'home'
    name = request.resolver_match.url_name or ''
    ns = request.resolver_match.namespace or ''
    if ns == 'instagram':
        return 'instagram'
    if name == 'panel_dashboard':
        return 'home'
    if name in ('bot_settings', 'bot_flow_engine', 'subscriber_list', 'subscriber_detail'):
        return 'bot'
    if name.startswith('campaign_'):
        return 'marketing'
    if name in ('inbound_list', 'callback_log_list'):
        return 'audience'
    if name.startswith('catalog_'):
        return 'catalog'
    if name.startswith('panel_user_'):
        return 'settings'
    return 'home'


def _panel_product(request) -> str:
    """Which main product area the user is in: bot, miniapp, instagram, or home."""
    module = _panel_module(request)
    if module == 'instagram':
        return 'instagram'
    if module == 'catalog':
        return 'miniapp'
    if module in ('bot', 'marketing', 'audience', 'settings'):
        return 'bot'
    return 'home'


def _inbound_open_count(request, ws, active) -> int:
    if not request.user.is_authenticated or not ws or not ws.is_active:
        return 0
    try:
        return InboundMessage.objects.filter(
            subscriber__workspace=ws,
            subscriber__platform=active,
            is_support_request=True,
            is_support_read=False,
        ).count()
    except OperationalError:
        return 0


def panel_branding(request):
    try:
        ws = get_workspace_for_user(request.user) if request.user.is_authenticated else None
        active = get_active_platform(request, ws)
        branding = None
        if ws and ws.is_active and ws.has_platform_access(active):
            branding = BotSettings.get_for_platform(ws, active)
        allowed = allowed_platforms_for_workspace(ws)
        other_platform = ''
        other_platform_label = ''
        for value, label in allowed:
            if value != active:
                other_platform = value
                other_platform_label = label
                break
        return {
            'bot_branding': branding,
            'active_platform': active,
            'active_platform_label': platform_label(active),
            'available_platforms': allowed,
            'other_platform': other_platform,
            'other_platform_label': other_platform_label,
            'panel_workspace': ws,
            'has_miniapp_access': has_miniapp_access_for_request(request, ws),
            'has_instagram_access': has_instagram_access_for_request(request, ws),
            'panel_module': _panel_module(request),
            'panel_product': _panel_product(request),
            'inbound_open_count': _inbound_open_count(request, ws, active),
        }
    except OperationalError:
        return {
            'bot_branding': None,
            'active_platform': 'bale',
            'active_platform_label': 'بله',
            'available_platforms': allowed_platforms_for_workspace(None),
            'other_platform': '',
            'other_platform_label': '',
            'panel_workspace': None,
            'has_miniapp_access': False,
            'has_instagram_access': False,
            'panel_module': 'home',
            'panel_product': 'home',
            'inbound_open_count': 0,
        }
