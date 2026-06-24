from django.core.management.base import BaseCommand

from balebot.management.campaign_send_command import (
    add_campaign_send_arguments,
    run_campaign_send_command,
)


class Command(BaseCommand):
    help = (
        'ارسال کمپین‌های زمان‌بندی‌شده که به موعد رسیده‌اند و ادامهٔ کمپین‌های ناتمام. '
        'به‌جای Celery با cron هر ۱–۲ دقیقه اجرا کنید.'
    )

    def add_arguments(self, parser):
        add_campaign_send_arguments(parser)

    def handle(self, *args, **options):
        run_campaign_send_command(self, options)
