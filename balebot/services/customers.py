from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone

from balebot.models import CustomerProfile, Subscriber


_DIGIT_MAP = str.maketrans('\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669', '01234567890123456789')


def normalize_phone(value: str) -> str:
    raw = (value or '').translate(_DIGIT_MAP)
    digits = re.sub(r'\D+', '', raw)
    if digits.startswith('0098'):
        digits = digits[4:]
    elif digits.startswith('98'):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith('9'):
        digits = '0' + digits
    return digits[:16]


@transaction.atomic
def ensure_customer_for_subscriber(subscriber: Subscriber) -> CustomerProfile:
    if subscriber.customer_id:
        return subscriber.customer

    phone = normalize_phone(subscriber.phone_number)
    verified = bool(phone and subscriber.phone_verified_at)
    customer = None
    if verified:
        customer = (
            CustomerProfile.objects.select_for_update()
            .filter(
                workspace_id=subscriber.workspace_id,
                normalized_phone=phone,
                phone_verified_at__isnull=False,
            )
            .first()
        )
    if customer is None:
        customer = CustomerProfile.objects.create(
            workspace_id=subscriber.workspace_id,
            display_name=' '.join(
                p for p in (subscriber.first_name, subscriber.last_name) if p
            )[:255],
            normalized_phone=phone,
            phone_verified_at=subscriber.phone_verified_at if verified else None,
        )
    subscriber.customer = customer
    subscriber.save(update_fields=['customer', 'updated_at'])
    return customer


@transaction.atomic
def ensure_customer_for_instagram_contact(contact) -> CustomerProfile:
    if contact.customer_id:
        return contact.customer
    if contact.subscriber_id:
        customer = ensure_customer_for_subscriber(contact.subscriber)
    else:
        customer = CustomerProfile.objects.create(
            workspace_id=contact.workspace_id,
            display_name=(contact.display_name or contact.username or '')[:255],
            metadata={'source': 'instagram'},
        )
    contact.customer = customer
    contact.save(update_fields=['customer', 'updated_at'])
    return customer


@transaction.atomic
def link_subscriber_to_customer(*, subscriber: Subscriber, customer: CustomerProfile) -> Subscriber:
    if subscriber.workspace_id != customer.workspace_id:
        raise ValueError('workspace mismatch')
    current = ensure_customer_for_subscriber(subscriber)
    if current.pk != customer.pk and not current.subscribers.exclude(pk=subscriber.pk).exists():
        current.delete()
    subscriber.customer = customer
    subscriber.save(update_fields=['customer', 'updated_at'])
    return subscriber


def attach_order_customer(order) -> None:
    if order.customer_id:
        return
    if order.subscriber_id:
        order.customer = ensure_customer_for_subscriber(order.subscriber)
    elif order.instagram_contact_id:
        order.customer = ensure_customer_for_instagram_contact(order.instagram_contact)
    if order.customer_id:
        order.save(update_fields=['customer', 'updated_at'])
