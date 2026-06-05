"""کمک‌کننده‌های پلتفرم (بله / تلگرام) برای پنل و وب‌هوک."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from balebot.models import BotSettings, Platform, Workspace
from balebot.workspace import get_workspace_for_user

SESSION_ACTIVE_PLATFORM_KEY = 'panel_active_platform'


def normalize_platform(value: str | None) -> str:
    if value == Platform.TELEGRAM:
        return Platform.TELEGRAM
    return Platform.BALE


def all_platforms() -> list[tuple[str, str]]:
    return [(Platform.BALE, platform_label(Platform.BALE)), (Platform.TELEGRAM, platform_label(Platform.TELEGRAM))]


def allowed_platforms_for_workspace(workspace: Workspace | None) -> list[tuple[str, str]]:
    if workspace is None:
        return all_platforms()
    result: list[tuple[str, str]] = []
    if workspace.allow_bale:
        result.append((Platform.BALE, platform_label(Platform.BALE)))
    if workspace.allow_telegram:
        result.append((Platform.TELEGRAM, platform_label(Platform.TELEGRAM)))
    return result


def _resolve_active_platform(request: HttpRequest, workspace: Workspace | None) -> str:
    raw = request.session.get(SESSION_ACTIVE_PLATFORM_KEY)
    platform = normalize_platform(raw)
    allowed = [value for value, _ in allowed_platforms_for_workspace(workspace)]
    if allowed and platform not in allowed:
        platform = allowed[0]
        request.session[SESSION_ACTIVE_PLATFORM_KEY] = platform
    return platform


def get_active_platform(request: HttpRequest, workspace: Workspace | None = None) -> str:
    if workspace is None and request.user.is_authenticated:
        workspace = get_workspace_for_user(request.user)
    return _resolve_active_platform(request, workspace)


def set_active_platform(request: HttpRequest, platform: str, workspace: Workspace | None = None) -> str:
    platform = normalize_platform(platform)
    if workspace is None and request.user.is_authenticated:
        workspace = get_workspace_for_user(request.user)
    allowed = {value for value, _ in allowed_platforms_for_workspace(workspace)}
    if allowed and platform not in allowed:
        raise PermissionDenied
    request.session[SESSION_ACTIVE_PLATFORM_KEY] = platform
    return platform


def require_workspace_for_request(request: HttpRequest) -> Workspace:
    ws = get_workspace_for_user(request.user)
    if ws is None or not ws.is_active:
        raise PermissionDenied
    return ws


def get_bot_settings_for_request(request: HttpRequest) -> BotSettings:
    workspace = require_workspace_for_request(request)
    platform = get_active_platform(request, workspace)
    if not workspace.has_platform_access(platform):
        raise PermissionDenied
    return BotSettings.get_for_platform(workspace, platform)


def platform_label(platform: str) -> str:
    if platform == Platform.TELEGRAM:
        return 'تلگرام'
    return 'بله'
