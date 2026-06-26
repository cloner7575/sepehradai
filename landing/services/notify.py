import logging

from django.conf import settings

from balebot.models import BotSettings, CatalogSettings, Platform
from balebot.services import messenger_api
from balebot.services.messenger_api import MessengerAPIError
from landing.models import Lead

logger = logging.getLogger(__name__)


def _resolve_admin_chat_id(catalog: CatalogSettings) -> int | str | None:
    override = (getattr(settings, 'LANDING_ADMIN_CHAT_ID', '') or '').strip()
    if override:
        try:
            return int(override)
        except ValueError:
            logger.warning('LANDING_ADMIN_CHAT_ID is not a valid integer: %s', override)
    return catalog.admin_notify_chat_id


def format_lead_message(lead: Lead) -> str:
    business = lead.business_name or '—'
    business_type = lead.business_type_display()
    messenger = lead.get_messenger_display_fa()
    return (
        'سرنخ جدید 🎯\n'
        f'نام: {lead.name}\n'
        f'کسب‌وکار: {business} ({business_type})\n'
        f'موبایل: {lead.phone}\n'
        f'پیام‌رسان: {messenger}'
    )


def notify_lead_via_bale(lead: Lead) -> bool:
    try:
        cfg = BotSettings.get_solo()
    except BotSettings.DoesNotExist:
        logger.warning('Lead notify skipped: no workspace/BotSettings found.')
        return False

    if not cfg.has_bot_token():
        logger.warning('Lead notify skipped: Bale bot token not configured.')
        return False

    catalog = CatalogSettings.get_for_platform(cfg.workspace, Platform.BALE)
    chat_id = _resolve_admin_chat_id(catalog)
    if not chat_id:
        logger.warning('Lead notify skipped: admin chat_id not configured.')
        return False

    text = format_lead_message(lead)
    if lead.note:
        text += f'\nتوضیحات: {lead.note[:500]}'

    try:
        messenger_api.send_message(
            Platform.BALE,
            chat_id,
            text[:4096],
            settings=cfg,
        )
        return True
    except MessengerAPIError:
        logger.exception('Failed to send lead notification to Bale.')
        return False
