"""اعطای دسترسی محتوا پس از پرداخت موفق."""

from __future__ import annotations

import logging

from django.db import transaction

from balebot.models import (
    BotSettings,
    CatalogEntitlement,
    CatalogItem,
    CatalogItemMember,
    CatalogOrder,
    CatalogOrderLine,
)
from balebot.services import messenger_api

logger = logging.getLogger(__name__)


def _grant_item_entitlement(
    *,
    order_line: CatalogOrderLine,
    item: CatalogItem,
) -> tuple[CatalogEntitlement | None, bool]:
    order = order_line.order
    if order.subscriber_id is None:
        return None, False
    entitlement, created = CatalogEntitlement.objects.get_or_create(
        subscriber_id=order.subscriber_id,
        item=item,
        defaults={
            'workspace_id': order.workspace_id,
            'platform': order.platform,
            'source_order_line': order_line,
        },
    )
    return entitlement, created


def grant_order_entitlements(order: CatalogOrder) -> list[CatalogItem]:
    """پس از پرداخت، دسترسی به آیتم‌های دیجیتال را ثبت می‌کند."""
    if order.status != CatalogOrder.Status.PAID:
        return []
    if order.subscriber_id is None:
        return []

    granted: list[CatalogItem] = []
    with transaction.atomic():
        for line in order.lines.select_related('item').all():
            item = line.item
            if item is None:
                continue
            item_type = item.normalized_item_type()
            if item_type in (CatalogItem.ItemType.COURSE, CatalogItem.ItemType.PACKAGE):
                members = (
                    CatalogItemMember.objects.filter(parent=item)
                    .select_related('child')
                    .order_by('sort_order', 'id')
                )
                for member in members:
                    _ent, created = _grant_item_entitlement(order_line=line, item=member.child)
                    if created:
                        granted.append(member.child)
                _ent, created = _grant_item_entitlement(order_line=line, item=item)
                if created:
                    granted.append(item)
            elif item_type in (CatalogItem.ItemType.VIDEO, CatalogItem.ItemType.DOWNLOAD):
                if item.requires_content_access() or item.is_buyable():
                    _ent, created = _grant_item_entitlement(order_line=line, item=item)
                    if created:
                        granted.append(item)

    if granted:
        _notify_content_access(order, granted)
    return granted


def _notify_content_access(order: CatalogOrder, items: list[CatalogItem]) -> None:
    try:
        cfg = BotSettings.get_for_platform(order.workspace, order.platform)
        sub = order.subscriber
        if not sub:
            return
        titles = '\n'.join(f'• {item.title}' for item in items[:10])
        extra = ''
        if len(items) > 10:
            extra = f'\nو {len(items) - 10} مورد دیگر…'
        text = (
            f'🎉 دسترسی محتوای شما فعال شد.\n'
            f'شماره سفارش: #{order.pk}\n\n'
            f'{titles}{extra}\n\n'
            f'برای مشاهده، دوباره وارد مینی‌اپ شوید.'
        )
        messenger_api.send_message(
            order.platform,
            sub.chat_id,
            text,
            settings=cfg,
        )
    except messenger_api.MessengerAPIError:
        logger.exception('Failed to notify content access for order %s', order.pk)
