"""کمک‌کننده‌های workspace برای پنل و ساخت کاربر."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from balebot.models import BotSettings, Workspace

User = get_user_model()


def get_workspace_for_user(user) -> Workspace | None:
    if not user.is_authenticated:
        return None
    try:
        return user.workspace
    except Workspace.DoesNotExist:
        return None


def user_has_panel_access(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    ws = get_workspace_for_user(user)
    return bool(user.is_staff and ws and ws.is_active)


def ensure_bot_settings_for_workspace(workspace: Workspace) -> None:
    for platform in workspace.allowed_platforms():
        BotSettings.get_for_platform(workspace, platform)


def create_panel_user(
    *,
    username: str,
    password: str,
    workspace_name: str,
    email: str = '',
    is_active: bool = True,
    allow_bale: bool = True,
    allow_telegram: bool = True,
) -> tuple[User, Workspace]:
    if not allow_bale and not allow_telegram:
        raise ValueError('حداقل یک پلتفرم باید انتخاب شود.')
    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_staff=True,
            is_superuser=False,
            is_active=is_active,
        )
        workspace = Workspace.objects.create(
            name=workspace_name.strip() or username,
            owner=user,
            is_active=is_active,
            allow_bale=allow_bale,
            allow_telegram=allow_telegram,
        )
        ensure_bot_settings_for_workspace(workspace)
    return user, workspace
