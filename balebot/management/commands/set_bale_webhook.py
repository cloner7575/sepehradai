from django.conf import settings
from django.core.management.base import BaseCommand

from balebot.services import bale_api


class Command(BaseCommand):
    help = 'فراخوانی setWebhook برای بازوی بله'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            nargs='?',
            default=None,
            help='آدرس کامل HTTPS وب‌هوک (مثلاً https://example.com/bale/webhook/secret/)',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='حذف وب‌هوک (برگشت به getUpdates)',
        )

    def handle(self, *args, **options):
        if not settings.BALE_BOT_TOKEN:
            self.stderr.write(self.style.ERROR('BALE_BOT_TOKEN خالی است.'))
            return

        if options['delete']:
            bale_api.delete_webhook()
            self.stdout.write(self.style.SUCCESS('وب‌هوک حذف شد.'))
            return

        url = options['url'] or getattr(settings, 'BALE_WEBHOOK_PUBLIC_URL', '') or ''
        if not url.strip():
            self.stderr.write(
                self.style.ERROR(
                    'آدرس وب‌هوک را به صورت آرگومنت یا متغیر محیطی BALE_WEBHOOK_PUBLIC_URL بدهید.'
                )
            )
            return

        bale_api.set_webhook(url.strip())
        self.stdout.write(self.style.SUCCESS(f'وب‌هوک تنظیم شد: {url.strip()}'))
