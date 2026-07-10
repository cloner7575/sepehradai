"""بررسی دسترسی کاربر به محتوای دیجیتال کاتالوگ."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from balebot.models import CatalogEntitlement, CatalogItem, CatalogItemMember, Subscriber


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
    if not parent_ids:
        return False
    return CatalogEntitlement.objects.filter(
        subscriber=subscriber,
        item_id__in=parent_ids,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
    ).exists()


def subscriber_entitled_item_ids(subscriber: Subscriber) -> set[int]:
    now = timezone.now()
    direct = set(
        CatalogEntitlement.objects.filter(subscriber=subscriber)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list('item_id', flat=True)
    )
    if not direct:
        return set()
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
    return direct | child_ids | preview_ids | free_paid_content


def media_is_locked(item: CatalogItem, media, subscriber: Subscriber | None) -> bool:
    if media.media_type == CatalogItem.MediaType.IMAGE:
        return False
    if not item.requires_content_access():
        return False
    return not subscriber_has_item_access(subscriber, item)
