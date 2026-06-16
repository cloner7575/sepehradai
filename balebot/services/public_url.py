"""آدرس عمومی سرور — از تنظیمات Django (BASE_URL) یا فیلد BotSettings."""

from __future__ import annotations

from django.conf import settings

from balebot.models import Platform
from balebot.services.webhook_setup import normalize_public_url


def get_public_base_url_from_config(*, platform: str = Platform.BALE) -> str:
    raw = (getattr(settings, 'BASE_URL', '') or '').strip()
    if not raw:
        return ''
    return normalize_public_url(raw, platform=platform)


def resolve_public_base_url(bot_settings, *, platform: str | None = None) -> str:
    platform = platform or getattr(bot_settings, 'platform', Platform.BALE) or Platform.BALE
    from_config = get_public_base_url_from_config(platform=platform)
    if from_config:
        return from_config
    stored = getattr(bot_settings, 'webhook_public_url', '') or ''
    return normalize_public_url(stored, platform=platform)


def ensure_webhook_config(bot_settings) -> list[str]:
    """رمز وب‌هوک و آدرس عمومی را در صورت نیاز از تنظیمات سرور ست می‌کند."""
    from balebot.models import generate_webhook_secret

    update_fields: list[str] = []
    if not (bot_settings.webhook_secret or '').strip():
        bot_settings.webhook_secret = generate_webhook_secret()
        update_fields.append('webhook_secret')

    public_url = get_public_base_url_from_config(platform=bot_settings.platform)
    if public_url and (bot_settings.webhook_public_url or '').strip() != public_url:
        bot_settings.webhook_public_url = public_url
        update_fields.append('webhook_public_url')

    return update_fields
