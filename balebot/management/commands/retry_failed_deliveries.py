from django.core.management.base import BaseCommand

from balebot.models import CampaignDelivery


class Command(BaseCommand):
    help = 'تبدیل تحویل‌های ناموفق به «در انتظار» برای تلاش مجدد توسط process_campaigns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--campaign',
            type=int,
            default=None,
            help='محدود به شناسهٔ کمپین',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='حداکثر تعداد رکورد برای بازنشانی',
        )

    def handle(self, *args, **options):
        campaign_id = options.get('campaign')
        limit = options['limit']

        qs = CampaignDelivery.objects.filter(status=CampaignDelivery.DeliveryStatus.FAILED)
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        ids = list(qs.values_list('pk', flat=True)[:limit])
        updated = CampaignDelivery.objects.filter(pk__in=ids).update(
            status=CampaignDelivery.DeliveryStatus.PENDING,
            error_message='',
        )
        self.stdout.write(self.style.SUCCESS(f'{updated} رکورد به حالت انتظار بازگردانده شد.'))
