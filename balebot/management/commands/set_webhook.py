from django.core.management.base import BaseCommand

from balebot.models import BotSettings, Platform
from balebot.services import messenger_api


class Command(BaseCommand):
    help = 'فراخوانی setWebhook برای ربات بله یا تلگرام (توکن از پنل/دیتابیس)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--platform',
            choices=[Platform.BALE, Platform.TELEGRAM],
            default=Platform.BALE,
            help='پلتفرم (پیش‌فرض: bale)',
        )
        parser.add_argument(
            'url',
            nargs='?',
            default=None,
            help='آدرس کامل HTTPS وب‌هوک',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='حذف وب‌هوک (برگشت به getUpdates)',
        )

    def handle(self, *args, **options):
        platform = options['platform']
        cfg = BotSettings.objects.filter(platform=platform).first()
        if cfg is None or not cfg.has_bot_token():
            self.stderr.write(self.style.ERROR(f'توکن ربات {platform} در پنل تنظیم نشده است.'))
            return

        if options['delete']:
            messenger_api.delete_webhook(platform)
            self.stdout.write(self.style.SUCCESS('وب‌هوک حذف شد.'))
            return

        url = (options['url'] or cfg.build_webhook_url() or '').strip()
        if not url:
            self.stderr.write(
                self.style.ERROR(
                    'آدرس وب‌هوک را به صورت آرگومنت بدهید یا webhook_public_url و webhook_secret را در پنل تنظیم کنید.'
                )
            )
            return

        messenger_api.set_webhook(platform, url)
        self.stdout.write(self.style.SUCCESS(f'وب‌هوک تنظیم شد: {url}'))
