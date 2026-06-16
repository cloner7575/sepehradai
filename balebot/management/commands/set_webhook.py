from django.core.management.base import BaseCommand

from balebot.models import BotSettings, Platform, Workspace
from balebot.services import messenger_api
from balebot.services.public_url import ensure_webhook_config


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
            '--workspace',
            type=int,
            default=None,
            help='شناسه workspace (پیش‌فرض: اولین workspace)',
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
        ws_id = options['workspace']
        if ws_id:
            workspace = Workspace.objects.filter(pk=ws_id).first()
        else:
            workspace = Workspace.objects.order_by('id').first()
        if workspace is None:
            self.stderr.write(self.style.ERROR('هیچ workspaceای یافت نشد.'))
            return

        cfg = BotSettings.objects.filter(workspace=workspace, platform=platform).first()
        if cfg is None or not cfg.has_bot_token():
            self.stderr.write(
                self.style.ERROR(f'توکن ربات {platform} برای workspace {workspace.id} تنظیم نشده است.'),
            )
            return

        if options['delete']:
            messenger_api.delete_webhook(platform, settings=cfg)
            self.stdout.write(self.style.SUCCESS('وب‌هوک حذف شد.'))
            return

        update_fields = ensure_webhook_config(cfg)
        if update_fields:
            update_fields.append('updated_at')
            cfg.save(update_fields=list(dict.fromkeys(update_fields)))

        url = (options['url'] or cfg.build_webhook_url() or '').strip()
        if not url:
            self.stderr.write(
                self.style.ERROR(
                    'آدرس وب‌هوک را به صورت آرگومنت بدهید یا BASE_URL را در تنظیمات سرور تنظیم کنید.',
                ),
            )
            return

        messenger_api.set_webhook(platform, url, settings=cfg)
        self.stdout.write(self.style.SUCCESS(f'وب‌هوک تنظیم شد: {url}'))
