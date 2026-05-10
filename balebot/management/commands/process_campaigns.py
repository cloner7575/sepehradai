from django.conf import settings
from django.core.management.base import BaseCommand

from balebot.services.campaign_runner import process_due_campaigns_batch


class Command(BaseCommand):
    help = 'پردازش کمپین‌های در صف / در حال ارسال و ارسال به مشترکین فعال ثبت‌نام‌شده.'

    def handle(self, *args, **options):
        if not settings.BALE_BOT_TOKEN:
            self.stderr.write(self.style.ERROR('BALE_BOT_TOKEN خالی است.'))
            return

        process_due_campaigns_batch(
            log_line=lambda m: self.stdout.write(m),
            err_line=lambda m: self.stderr.write(m),
        )
