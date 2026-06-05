"""ارسال یک پیام کمپین به یک چت."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from balebot.models import BotSettings, Campaign
from balebot.services import messenger_api
from balebot.services.keyboard_layout import flatten_rows


def build_inline_markup(campaign: Campaign) -> dict | None:
    flat = flatten_rows(campaign.inline_keyboard)
    if not flat:
        return None
    rows: list[list[dict[str, str]]] = []
    for ri, row in enumerate(flat):
        out_row = []
        for ci, btn in enumerate(row):
            if isinstance(btn, dict):
                text = (btn.get('text') or '').strip() or '…'
            else:
                text = str(btn)[:64]
            cid = f'c{campaign.id}_{ri}_{ci}'
            out_row.append({'text': text[:64], 'callback_data': cid[:64]})
        rows.append(out_row)
    return {'inline_keyboard': rows}


def send_campaign_to_chat(chat_id: int | str, campaign: Campaign) -> dict:
    platform = campaign.platform
    settings = BotSettings.get_for_platform(campaign.workspace, platform)
    markup = build_inline_markup(campaign)
    ct = campaign.content_type
    body = campaign.body or ''

    media_path = None
    if campaign.media:
        media_path = Path(campaign.media.path)

    if ct == Campaign.ContentType.TEXT:
        return messenger_api.send_message(
            platform, chat_id, body, settings=settings, reply_markup=markup,
        )

    if ct == Campaign.ContentType.TEXT_BUTTONS:
        if not markup:
            return messenger_api.send_message(platform, chat_id, body, settings=settings)
        return messenger_api.send_message(
            platform, chat_id, body, settings=settings, reply_markup=markup,
        )

    if ct == Campaign.ContentType.PHOTO:
        if not media_path or not media_path.is_file():
            raise messenger_api.MessengerAPIError('فایل تصویر کمپین یافت نشد.')
        return messenger_api.send_photo(
            platform,
            chat_id,
            settings=settings,
            photo_path=media_path,
            caption=body,
            reply_markup=markup,
        )

    if ct == Campaign.ContentType.VIDEO:
        if not media_path or not media_path.is_file():
            raise messenger_api.MessengerAPIError('فایل ویدیوی کمپین یافت نشد.')
        return messenger_api.send_video(
            platform,
            chat_id,
            settings=settings,
            video_path=media_path,
            caption=body,
            reply_markup=markup,
        )

    if ct == Campaign.ContentType.VOICE:
        if not media_path or not media_path.is_file():
            raise messenger_api.MessengerAPIError('فایل صوتی کمپین یافت نشد.')
        return messenger_api.send_voice(
            platform,
            chat_id,
            settings=settings,
            voice_path=media_path,
            caption=body,
            reply_markup=markup,
        )

    if ct == Campaign.ContentType.DOCUMENT:
        if not media_path or not media_path.is_file():
            raise messenger_api.MessengerAPIError('فایل سند کمپین یافت نشد.')
        return messenger_api.send_document(
            platform,
            chat_id,
            settings=settings,
            document_path=media_path,
            caption=body,
            reply_markup=markup,
        )

    raise messenger_api.MessengerAPIError(f'نوع محتوای نامعتبر: {ct}')


def ignore_setting_delay() -> float:
    return float(settings.CAMPAIGN_SEND_DELAY_MS) / 1000.0
