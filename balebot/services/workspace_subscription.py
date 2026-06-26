"""بررسی فعال بودن اشتراک workspace برای قطع/اجازه عملیات runtime."""

from __future__ import annotations

from balebot.models import Workspace

SUBSCRIPTION_EXPIRING_SOON_DAYS = 7

BLOCK_REASON_EXPIRED = 'اشتراک فروشگاه منقضی شده است. با پشتیبانی تماس بگیرید.'
BLOCK_REASON_INACTIVE = 'حساب پنل غیرفعال است.'


def workspace_can_operate(workspace: Workspace | None) -> bool:
    if workspace is None:
        return False
    return workspace.is_subscription_active()


def workspace_block_reason(workspace: Workspace | None) -> str | None:
    if workspace is None:
        return BLOCK_REASON_INACTIVE
    if not workspace.is_active:
        return BLOCK_REASON_INACTIVE
    if workspace.subscription_expires_at is not None and not workspace.is_subscription_active():
        return BLOCK_REASON_EXPIRED
    return None


def pause_campaign_if_subscription_lapsed(campaign) -> bool:
    """
    اگر اشتراک workspace منقضی شده، کمپین را لغو می‌کند.
    خروجی: True اگر کمپین متوقف شد.
    """
    from balebot.models import Campaign

    workspace = campaign.workspace
    if workspace_can_operate(workspace):
        return False
    if campaign.status in (Campaign.Status.COMPLETED, Campaign.Status.CANCELLED):
        return False
    campaign.status = Campaign.Status.CANCELLED
    campaign.save(update_fields=['status', 'updated_at'])
    return True
