"""اجرای ارسال کمپین (پنل وب و دستور دوره‌ای process_campaigns)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.conf import settings
from django.utils import timezone

from balebot.models import Campaign, CampaignDelivery, Subscriber
from balebot.services import bale_api
from balebot.services.campaign_send import ignore_setting_delay, send_campaign_to_chat

logger = logging.getLogger(__name__)


def transition_queued_to_sending_if_due(campaign: Campaign, now) -> bool:
    """
    کمپین «در صف» را اگر زمانش رسیده به «در حال ارسال» برمی‌گرداند.
    اگر هنوز زمان نرسیده، False (بدون تغییر وضعیت).
    """
    if campaign.status != Campaign.Status.QUEUED:
        return True
    if campaign.scheduled_at and campaign.scheduled_at > now:
        return False
    campaign.status = Campaign.Status.SENDING
    campaign.started_at = now
    campaign.save(update_fields=['status', 'started_at', 'updated_at'])
    return True


def run_delivery_pass_for_campaign(
    campaign: Campaign,
    *,
    delay: float,
    err_line: Callable[[str], None] | None = None,
) -> tuple[int, int]:
    """
    یک پاس ارسال برای کمپین در وضعیت SENDING.
    خروجی: (تعداد ارسال موفق در این پاس، تعداد خطا در این پاس)
    """
    sent_here = 0
    fail_here = 0
    subs = Subscriber.objects.filter(is_active=True, is_registered=True).order_by('id')

    for sub in subs.iterator():
        deliv, _ = CampaignDelivery.objects.get_or_create(
            campaign=campaign,
            subscriber=sub,
            defaults={'status': CampaignDelivery.DeliveryStatus.PENDING},
        )
        if deliv.status == CampaignDelivery.DeliveryStatus.SENT:
            continue

        try:
            send_campaign_to_chat(sub.chat_id, campaign)
        except Exception as e:  # noqa: BLE001
            deliv.status = CampaignDelivery.DeliveryStatus.FAILED
            deliv.error_message = str(e)[:2000]
            deliv.save(update_fields=['status', 'error_message'])
            line = f'خطا برای subscriber={sub.id}: {e}'
            if err_line:
                err_line(line)
            else:
                logger.warning('%s', line)
            if isinstance(e, bale_api.BaleAPIError) and getattr(e, 'payload', None):
                bale_api.sleep_after_rate_limit(e.payload)
            if isinstance(e, bale_api.BaleAPIError):
                logger.warning('Bale API error: %s', e)
            else:
                logger.exception('Unexpected campaign send error')
            time.sleep(delay)
            fail_here += 1
            continue

        deliv.status = CampaignDelivery.DeliveryStatus.SENT
        deliv.sent_at = timezone.now()
        deliv.error_message = ''
        deliv.save(update_fields=['status', 'sent_at', 'error_message'])
        sent_here += 1
        time.sleep(delay)

    pending = CampaignDelivery.objects.filter(
        campaign=campaign,
        status=CampaignDelivery.DeliveryStatus.PENDING,
    ).exists()
    if not pending:
        campaign.status = Campaign.Status.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'updated_at'])

    return sent_here, fail_here


def process_due_campaigns_batch(
    *,
    log_line: Callable[[str], None] | None = None,
    err_line: Callable[[str], None] | None = None,
) -> None:
    """تمام کمپین‌های سررسید در صف / در حال ارسال (برای cron یا دستور مدیریتی)."""
    now = timezone.now()
    delay = ignore_setting_delay()

    campaigns = Campaign.objects.filter(
        status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
    )

    for campaign in campaigns:
        if campaign.status == Campaign.Status.QUEUED:
            if not transition_queued_to_sending_if_due(campaign, now):
                continue
            if log_line:
                log_line(f'شروع کمپین {campaign.id}: {campaign.title}')
        elif campaign.status != Campaign.Status.SENDING:
            continue

        campaign.refresh_from_db()
        if campaign.status != Campaign.Status.SENDING:
            continue

        run_delivery_pass_for_campaign(campaign, delay=delay, err_line=err_line)

        if log_line:
            campaign.refresh_from_db()
            if campaign.status == Campaign.Status.COMPLETED:
                log_line(f'کمپین {campaign.id} تکمیل شد.')


def run_single_campaign_web(campaign_id: int) -> tuple[bool, str]:
    """
    یک کمپین را بلافاصله پردازش می‌کند (پس از قرار گرفتن در صف از پنل).
    برای زمان‌بندی‌شدهٔ آینده فراخوانی نشود.
    """
    if not settings.BALE_BOT_TOKEN:
        return False, 'توکن بازو (BALE_BOT_TOKEN) تنظیم نشده است.'

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return False, 'کمپین یافت نشد.'

    if campaign.status not in (
        Campaign.Status.QUEUED,
        Campaign.Status.SENDING,
    ):
        return False, 'کمپین در وضعیت قابل ارسال نیست.'

    now = timezone.now()
    delay = ignore_setting_delay()

    if campaign.status == Campaign.Status.QUEUED:
        if not transition_queued_to_sending_if_due(campaign, now):
            return (
                True,
                'این کمپین زمان‌بندی‌شده هنوز به موعد نرسیده؛ در صف می‌ماند.',
            )

    campaign.refresh_from_db()
    if campaign.status != Campaign.Status.SENDING:
        return False, 'شروع ارسال ممکن نشد.'

    sent, failed = run_delivery_pass_for_campaign(campaign, delay=delay, err_line=None)

    campaign.refresh_from_db()
    parts = [f'در این مرحله {sent} پیام ارسال شد.']
    if failed:
        parts.append(f'{failed} خطا ثبت شد.')
    if campaign.status == Campaign.Status.COMPLETED:
        parts.append('کمپین به‌طور کامل تمام شد.')
    return True, ' '.join(parts)
