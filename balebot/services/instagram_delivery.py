from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from balebot.models import (
    BotSettings,
    CatalogDeliveryToken,
    CatalogEntitlement,
    CatalogItem,
    CatalogOrder,
    Platform,
)
from balebot.services.customers import link_subscriber_to_customer


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


@transaction.atomic
def issue_delivery_link(order: CatalogOrder, platform: str) -> dict | None:
    if order.status != CatalogOrder.Status.PAID or order.source_channel != CatalogOrder.SourceChannel.INSTAGRAM:
        return None
    bot = BotSettings.objects.filter(
        workspace_id=order.workspace_id,
        platform=platform,
        is_enabled=True,
    ).first()
    username = (bot.bot_public_username if bot else '').strip().lstrip('@')
    if not bot or not username:
        return None
    canonical_keys = list(order.lines.values_list('item__canonical_key', flat=True))
    if not CatalogItem.objects.filter(
        workspace_id=order.workspace_id,
        platform=platform,
        canonical_key__in=canonical_keys,
        is_active=True,
    ).exists():
        return None
    now = timezone.now()
    CatalogDeliveryToken.objects.filter(
        order=order,
        platform=platform,
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).update(expires_at=now)
    raw = secrets.token_urlsafe(24)
    CatalogDeliveryToken.objects.create(
        order=order,
        platform=platform,
        token_digest=_digest(raw),
        expires_at=now + timedelta(minutes=30),
    )
    payload = f'igd_{raw}'
    if platform == Platform.TELEGRAM:
        url = f'https://t.me/{username}?start={payload}'
    else:
        url = f'https://ble.ir/{username}?start={payload}'
    return {'platform': platform, 'url': url, 'expires_in': 1800}


@transaction.atomic
def consume_delivery_token(raw: str, subscriber) -> int:
    token = (
        CatalogDeliveryToken.objects.select_for_update()
        .select_related('order')
        .filter(token_digest=_digest(raw))
        .first()
    )
    now = timezone.now()
    if not token or token.consumed_at or token.expires_at <= now:
        raise ValueError('delivery_token_invalid')
    order = token.order
    if order.status != CatalogOrder.Status.PAID:
        raise ValueError('order_not_paid')
    if subscriber.workspace_id != order.workspace_id or subscriber.platform != token.platform:
        raise ValueError('delivery_tenant_mismatch')
    if order.customer_id:
        link_subscriber_to_customer(subscriber=subscriber, customer=order.customer)
    granted = 0
    for line in order.lines.select_related('item'):
        item = CatalogItem.objects.filter(
            workspace_id=order.workspace_id,
            platform=token.platform,
            canonical_key=line.item.canonical_key,
            is_active=True,
        ).first()
        if not item:
            continue
        _, created = CatalogEntitlement.objects.get_or_create(
            workspace_id=order.workspace_id,
            platform=token.platform,
            subscriber=subscriber,
            item=item,
            defaults={'source_order_line': line},
        )
        granted += int(created)
    if not granted and not CatalogEntitlement.objects.filter(
        workspace_id=order.workspace_id,
        platform=token.platform,
        subscriber=subscriber,
        item__canonical_key__in=order.lines.values_list('item__canonical_key', flat=True),
    ).exists():
        raise ValueError('canonical_product_unavailable')
    token.consumed_at = now
    token.consumed_by = subscriber
    token.save(update_fields=['consumed_at', 'consumed_by'])
    return granted
