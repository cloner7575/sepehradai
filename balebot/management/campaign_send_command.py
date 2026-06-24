"""منطق مشترک دستورات ارسال کمپین زمان‌بندی‌شده."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from balebot.models import BotSettings, Campaign
from balebot.services.campaign_runner import process_due_campaigns_batch

if TYPE_CHECKING:
    from django.core.management.base import BaseCommand


def add_campaign_send_arguments(parser) -> None:
    parser.add_argument(
        '--campaign',
        type=int,
        default=None,
        metavar='ID',
        help='فقط یک کمپین مشخص (شناسه)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='فقط نمایش کمپین‌های قابل ارسال؛ بدون ارسال واقعی',
    )


def run_campaign_send_command(command: BaseCommand, options: dict) -> None:
    campaign_id = options.get('campaign')
    dry_run = options['dry_run']

    if campaign_id is not None:
        exists = Campaign.objects.filter(pk=campaign_id).exists()
        if not exists:
            command.stderr.write(command.style.ERROR(f'کمپین {campaign_id} یافت نشد.'))
            return

    if not dry_run and not BotSettings.objects.exclude(bot_token='').exists():
        command.stderr.write(
            command.style.ERROR('هیچ توکن رباتی در پنل تنظیم نشده است.'),
        )
        return

    now = timezone.now()
    command.stdout.write(
        f'زمان اجرا: {now.strftime("%Y-%m-%d %H:%M:%S")}'
        + (' — حالت dry-run' if dry_run else ''),
    )

    stats = process_due_campaigns_batch(
        campaign_id=campaign_id,
        dry_run=dry_run,
        log_line=lambda m: command.stdout.write(m),
        err_line=lambda m: command.stderr.write(command.style.WARNING(m)),
    )

    command.stdout.write('')
    command.stdout.write(
        command.style.SUCCESS(
            'خلاصه: '
            f'{stats["scanned"]} بررسی · '
            f'{stats["started"]} شروع · '
            f'{stats["completed"]} تکمیل · '
            f'{stats["sent"]} ارسال · '
            f'{stats["failed"]} خطا · '
            f'{stats["skipped_future"]} هنوز به موعد نرسیده',
        ),
    )
