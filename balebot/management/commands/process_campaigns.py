import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from balebot.models import Campaign, CampaignDelivery, Subscriber
from balebot.services import bale_api
from balebot.services.campaign_send import ignore_setting_delay, send_campaign_to_chat

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'پردازش کمپین‌های در صف / در حال ارسال و ارسال به مشترکین فعال ثبت‌نام‌شده.'

    def handle(self, *args, **options):
        if not settings.BALE_BOT_TOKEN:
            self.stderr.write(self.style.ERROR('BALE_BOT_TOKEN خالی است.'))
            return

        now = timezone.now()
        delay = ignore_setting_delay()

        campaigns = Campaign.objects.filter(
            status__in=(Campaign.Status.QUEUED, Campaign.Status.SENDING),
        )

        for campaign in campaigns:
            if campaign.status == Campaign.Status.QUEUED:
                if campaign.scheduled_at and campaign.scheduled_at > now:
                    continue
                campaign.status = Campaign.Status.SENDING
                campaign.started_at = now
                campaign.save(update_fields=['status', 'started_at', 'updated_at'])
                self.stdout.write(f'شروع کمپین {campaign.id}: {campaign.title}')

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
                    self.stderr.write(f'خطا برای subscriber={sub.id}: {e}')
                    if isinstance(e, bale_api.BaleAPIError) and getattr(e, 'payload', None):
                        bale_api.sleep_after_rate_limit(e.payload)
                    if isinstance(e, bale_api.BaleAPIError):
                        logger.warning('Bale API error: %s', e)
                    else:
                        logger.exception('Unexpected campaign send error')
                    time.sleep(delay)
                    continue

                deliv.status = CampaignDelivery.DeliveryStatus.SENT
                deliv.sent_at = timezone.now()
                deliv.error_message = ''
                deliv.save(update_fields=['status', 'sent_at', 'error_message'])
                time.sleep(delay)

            pending = CampaignDelivery.objects.filter(
                campaign=campaign,
                status=CampaignDelivery.DeliveryStatus.PENDING,
            ).exists()
            if not pending:
                campaign.status = Campaign.Status.COMPLETED
                campaign.completed_at = timezone.now()
                campaign.save(update_fields=['status', 'completed_at', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'کمپین {campaign.id} تکمیل شد.'))
