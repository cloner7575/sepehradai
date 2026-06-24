"""یادآوری سبد خرید رها‌شده — برای cron ساعتی."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone

from balebot.models import (
    BotSettings,
    CatalogCart,
    CatalogCartItem,
    CatalogOrder,
    CatalogSettings,
    DiscountCode,
)
from balebot.services import messenger_api


class Command(BaseCommand):
    help = 'ارسال پیام یادآوری برای سبدهای رها‌شده'

    def handle(self, *args, **options):
        now = timezone.now()
        sent = 0
        catalogs = CatalogSettings.objects.filter(is_enabled=True).select_related('workspace')

        for catalog in catalogs:
            hours = max(1, int(catalog.abandoned_cart_hours or 24))
            cutoff = now - timedelta(hours=hours)
            paid_exists = CatalogOrder.objects.filter(
                workspace=catalog.workspace,
                platform=catalog.platform,
                subscriber_id=OuterRef('subscriber_id'),
                status=CatalogOrder.Status.PAID,
                created_at__gte=cutoff,
            )
            carts = (
                CatalogCart.objects.filter(
                    workspace=catalog.workspace,
                    platform=catalog.platform,
                    updated_at__gte=cutoff - timedelta(days=7),
                    updated_at__lte=cutoff,
                    reminder_sent_at__isnull=True,
                )
                .annotate(has_items=Exists(CatalogCartItem.objects.filter(cart_id=OuterRef('pk'))))
                .filter(has_items=True)
                .annotate(has_paid=Exists(paid_exists))
                .filter(has_paid=False)
                .select_related('subscriber')
            )
            if not carts.exists():
                continue

            try:
                cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
            except Exception:
                continue

            for cart in carts:
                sub = cart.subscriber
                if not sub or not sub.is_active:
                    continue
                code = self._ensure_reminder_code(catalog)
                template = (
                    catalog.abandoned_cart_message_template
                    or 'سبد خریدت منتظرته 🛍 با کد {code} ۱۰٪ تخفیف بگیر.'
                )
                try:
                    text = template.format(code=code)
                except (KeyError, ValueError):
                    text = template.replace('{code}', code)
                try:
                    messenger_api.send_message(
                        catalog.platform,
                        sub.chat_id,
                        text,
                        settings=cfg,
                    )
                    cart.reminder_sent_at = now
                    cart.save(update_fields=['reminder_sent_at'])
                    sent += 1
                except messenger_api.MessengerAPIError:
                    self.stderr.write(f'Failed cart reminder for subscriber {sub.pk}')

        self.stdout.write(self.style.SUCCESS(f'Reminders sent: {sent}'))

    def _ensure_reminder_code(self, catalog: CatalogSettings) -> str:
        code = 'BACK10'
        dc, created = DiscountCode.objects.get_or_create(
            workspace=catalog.workspace,
            platform=catalog.platform,
            code=code,
            defaults={
                'kind': DiscountCode.Kind.PERCENT,
                'value': 10,
                'max_uses': None,
                'min_order_amount': 0,
                'is_active': True,
            },
        )
        if not created and not dc.is_active:
            dc.is_active = True
            dc.save(update_fields=['is_active', 'updated_at'])
        return dc.code
