from __future__ import annotations

from django.utils import timezone

from instagram.automation.models import InstagramContact, InstagramConversation
from instagram.automation.services.normalize import NormalizedEvent


def resolve_contact_from_event(
    *,
    connection,
    event: NormalizedEvent,
) -> InstagramContact:
    scoped = event.sender_scoped_id
    if not scoped:
        raise ValueError('sender_scoped_id missing')
    now = timezone.now()
    contact, created = InstagramContact.objects.get_or_create(
        connection=connection,
        instagram_scoped_user_id=scoped,
        defaults={
            'workspace_id': connection.workspace_id,
            'username': str((event.extra or {}).get('username') or ''),
            'display_name': str((event.extra or {}).get('username') or ''),
            'first_interaction_at': now,
            'last_interaction_at': now,
        },
    )
    if not created:
        InstagramContact.objects.filter(pk=contact.pk).update(last_interaction_at=now)
        contact.last_interaction_at = now
    if not contact.customer_id:
        from balebot.services.customers import ensure_customer_for_instagram_contact

        ensure_customer_for_instagram_contact(contact)
    return contact


def get_or_create_conversation(
    *,
    connection,
    contact: InstagramContact,
) -> InstagramConversation:
    conv, _ = InstagramConversation.objects.get_or_create(
        connection=connection,
        contact=contact,
        defaults={
            'workspace_id': connection.workspace_id,
            'status': InstagramConversation.Status.OPEN,
            'mode': InstagramConversation.Mode.AUTOMATION,
        },
    )
    return conv


def link_subscriber_manual(*, contact: InstagramContact, subscriber) -> InstagramContact:
    """اتصال دستی — merge خودکار فقط با شناسه مطمئن انجام می‌شود."""
    if subscriber.workspace_id != contact.workspace_id:
        raise ValueError('workspace mismatch')
    from balebot.services.customers import (
        ensure_customer_for_subscriber,
        link_subscriber_to_customer,
    )
    customer = contact.customer or ensure_customer_for_subscriber(subscriber)
    link_subscriber_to_customer(subscriber=subscriber, customer=customer)
    contact.subscriber = subscriber
    contact.customer = customer
    contact.save(update_fields=['subscriber', 'customer', 'updated_at'])
    return contact
