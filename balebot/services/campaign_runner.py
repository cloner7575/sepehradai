"""اجرای ارسال کمپین (پنل وب و دستور دوره‌ای process_campaigns)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.utils import timezone

from balebot.models import BotSettings, Campaign, CampaignDelivery, Subscriber
from balebot.services import messenger_api
from balebot.services.audience import resolve_campaign_subscribers_qs
from balebot.services.campaign_send import ignore_setting_delay, send_campaign_to_chat

logger = logging.getLogger(__name__)


def campaign_audience_total(campaign: Campaign) -> int:
    snapshot_ids = [int(sid) for sid in (campaign.audience_snapshot or []) if str(sid).isdigit()]
    if snapshot_ids:
        return len(snapshot_ids)
    return resolve_campaign_subscribers_qs(campaign).count()


def campaign_delivery_progress(campaign: Campaign) -> dict[str, int]:
    total = campaign_audience_total(campaign)
    sent = campaign.deliveries.filter(status=CampaignDelivery.DeliveryStatus.SENT).count()
    failed = campaign.deliveries.filter(status=CampaignDelivery.DeliveryStatus.FAILED).count()
    done = sent + failed
    pending = max(0, total - done)
    percent = min(100, round(done / total * 100)) if total else 0
    return {
        'total': total,
        'sent': sent,
        'failed': failed,
        'pending': pending,
        'done_count': done,
        'percent': percent,
    }


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
    max_messages: int | None = None,
    err_line: Callable[[str], None] | None = None,
) -> tuple[int, int]:
    """
    یک پاس ارسال برای کمپین در وضعیت SENDING.
    خروجی: (تعداد ارسال موفق در این پاس، تعداد خطا در این پاس)
    """
    sent_here = 0
    fail_here = 0
    attempted = 0
    snapshot_ids = [int(sid) for sid in (campaign.audience_snapshot or []) if str(sid).isdigit()]
    if snapshot_ids:
        subs = Subscriber.objects.filter(id__in=snapshot_ids).order_by('id')
    else:
        subs = resolve_campaign_subscribers_qs(campaign)

    for sub in subs.iterator():
        deliv, _ = CampaignDelivery.objects.get_or_create(
            campaign=campaign,
            subscriber=sub,
            defaults={'status': CampaignDelivery.DeliveryStatus.PENDING},
        )
        if deliv.status == CampaignDelivery.DeliveryStatus.SENT:
            continue

        if max_messages is not None and attempted >= max_messages:
            break
        attempted += 1

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
            if isinstance(e, messenger_api.MessengerAPIError) and getattr(e, 'payload', None):
                messenger_api.sleep_after_rate_limit(e.payload)
            if isinstance(e, messenger_api.MessengerAPIError):
                logger.warning('Messenger API error: %s', e)
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
    progress = campaign_delivery_progress(campaign)
    if not pending and progress['pending'] == 0:
        campaign.status = Campaign.Status.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'updated_at'])

    return sent_here, fail_here


def run_campaign_delivery_batch(
    campaign_id: int,
    *,
    batch_size: int | None = None,
) -> dict[str, Any]:
    """یک دسته از پیام‌های کمپین را ارسال می‌کند (برای پنل وب)."""
    batch_size = batch_size or getattr(settings, 'CAMPAIGN_SEND_BATCH_SIZE', 15)

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return {'ok': False, 'error': 'کمپین یافت نشد.'}

    if not BotSettings.get_for_platform(campaign.workspace, campaign.platform).has_bot_token():
        label = 'تلگرام' if campaign.platform == 'telegram' else 'بله'
        return {'ok': False, 'error': f'توکن ربات {label} در پنل تنظیم نشده است.'}

    if campaign.status == Campaign.Status.CANCELLED:
        return {'ok': False, 'error': 'کمپین لغو شده است.'}

    if campaign.status == Campaign.Status.COMPLETED:
        progress = campaign_delivery_progress(campaign)
        return {
            'ok': True,
            'done': True,
            'status': campaign.status,
            **progress,
        }

    now = timezone.now()
    if campaign.status == Campaign.Status.QUEUED:
        if not transition_queued_to_sending_if_due(campaign, now):
            progress = campaign_delivery_progress(campaign)
            return {
                'ok': True,
                'done': False,
                'waiting': True,
                'status': campaign.status,
                'message': 'هنوز به موعد زمان‌بندی نرسیده.',
                **progress,
            }
        campaign.refresh_from_db()

    if campaign.status != Campaign.Status.SENDING:
        if campaign.status == Campaign.Status.DRAFT:
            return {'ok': False, 'error': 'کمپین هنوز در صف قرار نگرفته.'}
        return {'ok': False, 'error': 'کمپین در وضعیت قابل ارسال نیست.'}

    delay = ignore_setting_delay()
    sent, failed = run_delivery_pass_for_campaign(
        campaign,
        delay=delay,
        max_messages=batch_size,
    )
    campaign.refresh_from_db()
    progress = campaign_delivery_progress(campaign)
    done = (
        campaign.status == Campaign.Status.COMPLETED
        or (progress['total'] > 0 and progress['pending'] == 0)
    )
    if done and campaign.status != Campaign.Status.COMPLETED:
        campaign.status = Campaign.Status.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'updated_at'])

    return {
        'ok': True,
        'done': done,
        'status': campaign.status,
        'batch_sent': sent,
        'batch_failed': failed,
        **progress,
    }


def process_due_campaigns_batch(
    *,
    log_line: Callable[[str], None] | None = None,
    err_line: Callable[[str], None] | None = None,
) -> None:
    """تمام کمپین‌های سررسید در صف / در حال ارسال (برای cron یا دستور مدیریتی)."""
    now = timezone.now()
    delay = ignore_setting_delay()
    batch_size = getattr(settings, 'CAMPAIGN_SEND_BATCH_SIZE', 15)

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

        while campaign.status == Campaign.Status.SENDING:
            run_delivery_pass_for_campaign(
                campaign,
                delay=delay,
                max_messages=batch_size,
                err_line=err_line,
            )
            campaign.refresh_from_db()
            progress = campaign_delivery_progress(campaign)
            if progress['pending'] == 0:
                break

        if log_line:
            campaign.refresh_from_db()
            if campaign.status == Campaign.Status.COMPLETED:
                log_line(f'کمپین {campaign.id} تکمیل شد.')


def run_single_campaign_web(campaign_id: int) -> tuple[bool, str]:
    """
    یک کمپین را بلافاصله پردازش می‌کند (پس از قرار گرفتن در صف از پنل).
    برای زمان‌بندی‌شدهٔ آینده فراخوانی نشود.
    """
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return False, 'کمپین یافت نشد.'

    if not BotSettings.get_for_platform(campaign.workspace, campaign.platform).has_bot_token():
        label = 'تلگرام' if campaign.platform == 'telegram' else 'بله'
        return False, f'توکن ربات {label} در پنل تنظیم نشده است.'

    if campaign.status not in (
        Campaign.Status.QUEUED,
        Campaign.Status.SENDING,
    ):
        return False, 'کمپین در وضعیت قابل ارسال نیست.'

    now = timezone.now()
    if campaign.status == Campaign.Status.QUEUED:
        if not transition_queued_to_sending_if_due(campaign, now):
            return (
                True,
                'این کمپین زمان‌بندی‌شده هنوز به موعد نرسیده؛ در صف می‌ماند.',
            )

    campaign.refresh_from_db()
    if campaign.status != Campaign.Status.SENDING:
        return False, 'شروع ارسال ممکن نشد.'

    batch_size = getattr(settings, 'CAMPAIGN_SEND_BATCH_SIZE', 15)
    sent, failed = run_delivery_pass_for_campaign(campaign, delay=ignore_setting_delay(), max_messages=batch_size)

    campaign.refresh_from_db()
    progress = campaign_delivery_progress(campaign)
    parts = [f'در این مرحله {sent} پیام ارسال شد.']
    if failed:
        parts.append(f'{failed} خطا ثبت شد.')
    if progress['pending'] > 0:
        parts.append(f'{progress["pending"]} نفر باقی‌مانده — ارسال از پنل ادامه می‌یابد.')
    elif campaign.status == Campaign.Status.COMPLETED:
        parts.append('کمپین به‌طور کامل تمام شد.')
    return True, ' '.join(parts)
