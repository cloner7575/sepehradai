"""کمک‌کننده‌های پلتفرم (بله / تلگرام) برای پنل و وب‌هوک."""

from __future__ import annotations

from django.http import HttpRequest

from balebot.models import BotSettings, Platform

SESSION_ACTIVE_PLATFORM_KEY = 'panel_active_platform'


def normalize_platform(value: str | None) -> str:
    if value == Platform.TELEGRAM:
        return Platform.TELEGRAM
    return Platform.BALE


def get_active_platform(request: HttpRequest) -> str:
    raw = request.session.get(SESSION_ACTIVE_PLATFORM_KEY)
    return normalize_platform(raw)


def set_active_platform(request: HttpRequest, platform: str) -> str:
    platform = normalize_platform(platform)
    request.session[SESSION_ACTIVE_PLATFORM_KEY] = platform
    return platform


def get_bot_settings_for_request(request: HttpRequest) -> BotSettings:
    return BotSettings.get_for_platform(get_active_platform(request))


def platform_label(platform: str) -> str:
    if platform == Platform.TELEGRAM:
        return 'تلگرام'
    return 'بله'


def all_platforms() -> list[tuple[str, str]]:
    return [(Platform.BALE, platform_label(Platform.BALE)), (Platform.TELEGRAM, platform_label(Platform.TELEGRAM))]
