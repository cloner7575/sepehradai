"""ارسال پاسخ تیکت پشتیبانی از پنل."""

from __future__ import annotations

import tempfile
from pathlib import Path

from balebot.models import BotSettings, InboundMessage, Subscriber, SupportTicketMessage
from balebot.services import messenger_api


def extract_file_id(api_response: dict, key: str) -> str:
    result = (api_response or {}).get('result') or {}
    payload = result.get(key)
    if isinstance(payload, list):
        last = payload[-1] if payload else {}
        return str((last or {}).get('file_id') or '')
    if isinstance(payload, dict):
        return str(payload.get('file_id') or '')
    return ''


def resolve_reply_to_message_id(parent_user_message: SupportTicketMessage) -> int | None:
    inbound = parent_user_message.inbound_message
    if inbound and inbound.messenger_message_id:
        return int(inbound.messenger_message_id)
    return None


def ensure_user_ticket_for_inbound(inbound: InboundMessage) -> SupportTicketMessage:
    ticket = SupportTicketMessage.objects.filter(
        inbound_message=inbound,
        sender=SupportTicketMessage.Sender.USER,
    ).first()
    if ticket:
        return ticket
    ticket = SupportTicketMessage.objects.create(
        subscriber=inbound.subscriber,
        sender=SupportTicketMessage.Sender.USER,
        kind=inbound.kind,
        text=inbound.text,
        file_id=inbound.file_id,
        inbound_message=inbound,
    )
    SupportTicketMessage.objects.filter(pk=ticket.pk).update(created_at=inbound.created_at)
    ticket.created_at = inbound.created_at
    return ticket


def sync_support_inbounds_into_tickets(inbounds) -> None:
    inbound_list = list(inbounds)
    if not inbound_list:
        return
    subscriber_ids = {row.subscriber_id for row in inbound_list}
    inbound_ids = {row.id for row in inbound_list}
    existing = set(
        SupportTicketMessage.objects.filter(
            subscriber_id__in=subscriber_ids,
            sender=SupportTicketMessage.Sender.USER,
            inbound_message_id__in=inbound_ids,
        ).values_list('inbound_message_id', flat=True)
    )
    missing = [row for row in inbound_list if row.id not in existing]
    if not missing:
        return
    SupportTicketMessage.objects.bulk_create(
        [
            SupportTicketMessage(
                subscriber=row.subscriber,
                sender=SupportTicketMessage.Sender.USER,
                kind=row.kind,
                text=row.text,
                file_id=row.file_id,
                inbound_message=row,
                created_at=row.created_at,
            )
            for row in missing
        ]
    )


def send_support_ticket_reply(
    *,
    subscriber: Subscriber,
    parent_user_message: SupportTicketMessage,
    text: str,
    media=None,
    reply_to_message_id: int | None = None,
) -> tuple[str, str, str]:
    """ارسال پاسخ به کاربر؛ خروجی: (kind, text_body, file_id)."""
    platform = subscriber.platform
    bot_settings = BotSettings.get_for_platform(subscriber.workspace, platform)
    msg = (text or '').strip()

    if media:
        return _send_media_reply(
            platform,
            subscriber.chat_id,
            bot_settings,
            media,
            msg,
            reply_to_message_id=reply_to_message_id,
        )

    messenger_api.send_message(
        platform,
        subscriber.chat_id,
        msg[:4096],
        settings=bot_settings,
        reply_to_message_id=reply_to_message_id,
    )
    return SupportTicketMessage.MessageKind.TEXT, msg[:4096], ''


def _send_media_reply(
    platform: str,
    chat_id: int | str,
    bot_settings: BotSettings,
    media,
    caption_text: str,
    *,
    reply_to_message_id: int | None = None,
) -> tuple[str, str, str]:
    suffix = Path(media.name or '').suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '.bin') as tmp:
        for chunk in media.chunks():
            tmp.write(chunk)
        temp_path = Path(tmp.name)

    caption = (caption_text or '').strip()[:1024]
    content_type = (getattr(media, 'content_type', '') or '').lower()
    try:
        if content_type.startswith('image/'):
            resp = messenger_api.send_photo(
                platform,
                chat_id,
                settings=bot_settings,
                photo_path=temp_path,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
            )
            return (
                SupportTicketMessage.MessageKind.PHOTO,
                caption,
                extract_file_id(resp, 'photo'),
            )
        if content_type.startswith('video/'):
            resp = messenger_api.send_video(
                platform,
                chat_id,
                settings=bot_settings,
                video_path=temp_path,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
            )
            return (
                SupportTicketMessage.MessageKind.VIDEO,
                caption,
                extract_file_id(resp, 'video'),
            )
        if content_type in {'audio/ogg', 'audio/opus'}:
            resp = messenger_api.send_voice(
                platform,
                chat_id,
                settings=bot_settings,
                voice_path=temp_path,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
            )
            return (
                SupportTicketMessage.MessageKind.VOICE,
                caption,
                extract_file_id(resp, 'voice'),
            )
        resp = messenger_api.send_document(
            platform,
            chat_id,
            settings=bot_settings,
            document_path=temp_path,
            caption=caption,
            reply_to_message_id=reply_to_message_id,
        )
        return (
            SupportTicketMessage.MessageKind.DOCUMENT,
            caption,
            extract_file_id(resp, 'document'),
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
