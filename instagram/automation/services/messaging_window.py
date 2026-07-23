from datetime import timedelta

from django.utils import timezone


MESSAGE_WINDOW_HOURS = 24


def messaging_window_expires_at(conversation):
    if not conversation or not conversation.last_customer_message_at:
        return None
    return conversation.last_customer_message_at + timedelta(hours=MESSAGE_WINDOW_HOURS)


def is_messaging_window_open(conversation) -> bool:
    expires_at = messaging_window_expires_at(conversation)
    return bool(expires_at and timezone.now() < expires_at)


class MessagingWindowClosed(ValueError):
    pass
