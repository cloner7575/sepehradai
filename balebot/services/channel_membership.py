"""بررسی عضویت کاربر در کانال از طریق Bot API."""

from __future__ import annotations

import logging

from balebot.models import BotSettings, CatalogSettings
from balebot.services import messenger_api

logger = logging.getLogger(__name__)

MEMBER_STATUSES = frozenset({'member', 'administrator', 'creator'})


def is_channel_member(catalog: CatalogSettings, user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال الزامی؛ در صورت خطا False برمی‌گرداند."""
    if not catalog.require_channel_membership:
        return True
    channel_id = (catalog.required_channel_id or '').strip()
    if not channel_id:
        return True

    cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
    if not (cfg.bot_token or '').strip():
        logger.warning('channel membership check skipped: no bot token for workspace %s', catalog.workspace_id)
        return False

    try:
        result = messenger_api.get_chat_member(
            catalog.platform,
            channel_id,
            user_id,
            settings=cfg,
        )
    except messenger_api.MessengerAPIError as exc:
        logger.warning('getChatMember failed for user %s channel %s: %s', user_id, channel_id, exc)
        return False

    member = result.get('result') or {}
    status = (member.get('status') or '').strip().lower()
    return status in MEMBER_STATUSES
