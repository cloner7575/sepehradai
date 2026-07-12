"""بررسی دسترسی کاربر به محتوای دیجیتال کاتالوگ."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from balebot.models import (
    CatalogEntitlement,
    CatalogItem,
    CatalogItemMedia,
    CatalogItemMember,
    CatalogOrder,
    CatalogOrderLine,
    Subscriber,
)


def _subscriber_paid_item_ids(subscriber: Subscriber) -> set[int]:
    """آیتم‌هایی که کاربر با سفارش پرداخت‌شده خریده (شامل اعضای دوره/پکیج)."""
    purchased = set(
        CatalogOrderLine.objects.filter(
            order__subscriber=subscriber,
            order__status=CatalogOrder.Status.PAID,
            order__workspace=subscriber.workspace,
            order__platform=subscriber.platform,
            item_id__isnull=False,
        ).values_list('item_id', flat=True)
    )
    if not purchased:
        return set()
    child_ids = set(
        CatalogItemMember.objects.filter(parent_id__in=purchased).values_list('child_id', flat=True)
    )
    return purchased | child_ids


def subscriber_has_item_access(subscriber: Subscriber | None, item: CatalogItem) -> bool:
    if item.is_free_content():
        return True
    if CatalogItemMember.objects.filter(child=item, is_preview=True).exists():
        return True
    if subscriber is None:
        return False
    if CatalogEntitlement.objects.filter(
        subscriber=subscriber,
        item=item,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
    ).exists():
        return True
    parent_ids = CatalogItemMember.objects.filter(child=item).values_list('parent_id', flat=True)
    if parent_ids and CatalogEntitlement.objects.filter(
        subscriber=subscriber,
        item_id__in=parent_ids,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
    ).exists():
        return True
    return item.pk in _subscriber_paid_item_ids(subscriber)


def _paid_group_children(item: CatalogItem) -> list[CatalogItem]:
    if not item.is_group_parent():
        return []
    children: list[CatalogItem] = []
    for member in item.group_members.select_related('child').order_by('sort_order', 'id'):
        child = member.child
        if not child.is_active or member.is_preview:
            continue
        if child.requires_content_access():
            children.append(child)
    return children


def subscriber_has_group_access(subscriber: Subscriber | None, item: CatalogItem) -> bool:
    """دسترسی به دوره/پکیج: خرید خود آیتم یا باز بودن همه قسمت‌های پولی."""
    if not item.is_group_parent():
        return subscriber_has_item_access(subscriber, item)
    if subscriber_has_item_access(subscriber, item):
        return True
    if subscriber is None:
        return False
    required = _paid_group_children(item)
    if not required:
        return False
    return all(subscriber_has_item_access(subscriber, child) for child in required)


def subscriber_entitled_item_ids(subscriber: Subscriber) -> set[int]:
    now = timezone.now()
    direct = set(
        CatalogEntitlement.objects.filter(subscriber=subscriber)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list('item_id', flat=True)
    )
    child_ids = set()
    if direct:
        child_ids = set(
            CatalogItemMember.objects.filter(parent_id__in=direct).values_list('child_id', flat=True)
        )
    preview_ids = set(
        CatalogItemMember.objects.filter(is_preview=True).values_list('child_id', flat=True)
    )
    free_paid_content = set(
        CatalogItem.objects.filter(
            workspace=subscriber.workspace,
            platform=subscriber.platform,
            is_active=True,
        )
        .filter(item_type__in=[CatalogItem.ItemType.DOWNLOAD, CatalogItem.ItemType.VIDEO])
        .filter(Q(price__isnull=True) | Q(price=0))
        .values_list('id', flat=True)
    )
    paid_order_ids = _subscriber_paid_item_ids(subscriber)
    return direct | child_ids | preview_ids | free_paid_content | paid_order_ids


def subscriber_library_item_ids(subscriber: Subscriber) -> set[int]:
    """دوره‌ها و پکیج‌های فایلی که کاربر به آن‌ها دسترسی دارد."""
    parents = CatalogItem.objects.filter(
        workspace=subscriber.workspace,
        platform=subscriber.platform,
        is_active=True,
        item_type__in=[CatalogItem.ItemType.COURSE, CatalogItem.ItemType.PACKAGE],
    )
    return {
        item.pk for item in parents
        if subscriber_has_group_access(subscriber, item)
    }


def subscriber_has_library(subscriber: Subscriber | None) -> bool:
    if subscriber is None:
        return False
    return bool(subscriber_library_item_ids(subscriber))


def media_is_locked(item: CatalogItem, media, subscriber: Subscriber | None) -> bool:
    if media.media_type == CatalogItemMedia.MediaType.IMAGE:
        return False
    if not item.requires_content_access():
        return False
    return not subscriber_has_item_access(subscriber, item)
