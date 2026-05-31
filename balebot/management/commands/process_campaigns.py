from balebot.models import BotSettings
from balebot.services.campaign_runner import process_due_campaigns_batch


class Command(BaseCommand):
    help = 'پردازش کمپین‌های در صف / در حال ارسال و ارسال به مشترکین فعال ثبت‌نام‌شده.'

    def handle(self, *args, **options):
        if not BotSettings.objects.exclude(bot_token='').exists():
            self.stderr.write(self.style.ERROR('هیچ توکن رباتی در پنل تنظیم نشده است.'))
            return

        process_due_campaigns_batch(
            log_line=lambda m: self.stdout.write(m),
            err_line=lambda m: self.stderr.write(m),
        )
