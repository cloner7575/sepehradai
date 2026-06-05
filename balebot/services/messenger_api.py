"""کلاینت HTTP یکپارچه برای API بله و تلگرام (Bot API-compatible)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests

from balebot.models import BotSettings, Platform

class MessengerAPIError(Exception):
    def __init__(self, message: str, error_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.payload = payload or {}


# Alias used across codebase during transition
BaleAPIError = MessengerAPIError


def get_api_base(platform: str) -> str:
    if platform == Platform.TELEGRAM:
        return 'https://api.telegram.org'
    return 'https://tapi.bale.ai'


def _resolve_settings(platform: str, settings: BotSettings | None) -> BotSettings:
    if settings is not None:
        return settings
    raise MessengerAPIError('تنظیمات ربات (BotSettings) برای فراخوانی API مشخص نشده است.')


def _bot_base_url(platform: str, settings: BotSettings | None = None) -> str:
    cfg = _resolve_settings(platform, settings)
    token = (cfg.bot_token or '').strip()
    if not token:
        label = 'تلگرام' if platform == Platform.TELEGRAM else 'بله'
        raise MessengerAPIError(f'توکن ربات {label} در پنل تنظیم نشده است.')
    base = get_api_base(platform).rstrip('/')
    return f'{base}/bot{token}/'


def call_method(
    platform: str,
    method: str,
    *,
    settings: BotSettings | None = None,
    json_body: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """فراخوانی متد API؛ در خطای منطقی MessengerAPIError می‌اندازد."""
    url = urljoin(_bot_base_url(platform, settings=settings), method)
    try:
        if files:
            r = requests.post(url, data=data or {}, files=files, timeout=timeout)
        elif json_body is not None:
            r = requests.post(url, json=json_body, timeout=timeout)
        elif data is not None:
            r = requests.post(url, data=data, timeout=timeout)
        else:
            r = requests.post(url, timeout=timeout)
    except requests.RequestException as e:
        raise MessengerAPIError(f'خطای شبکه: {e}') from e

    try:
        body = r.json()
    except json.JSONDecodeError as e:
        raise MessengerAPIError(f'پاسخ نامعتبر HTTP {r.status_code}: {r.text[:500]}') from e

    if not body.get('ok'):
        raise MessengerAPIError(
            body.get('description') or 'خطای نامشخص API',
            error_code=body.get('error_code'),
            payload=body,
        )
    return body


def get_me(platform: str, *, settings: BotSettings | None = None) -> dict[str, Any]:
    return call_method(platform, 'getMe', settings=settings)


def send_message(
    platform: str,
    chat_id: int | str,
    text: str,
    *,
    settings: BotSettings | None = None,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {'chat_id': chat_id, 'text': text}
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return call_method(platform, 'sendMessage', settings=settings, json_body=payload)


def send_photo(
    platform: str,
    chat_id: int | str,
    *,
    settings: BotSettings | None = None,
    photo_path: Path | None = None,
    photo_file_id: str | None = None,
    photo_file: Any | None = None,
    photo_filename: str | None = None,
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cap = (caption or '').strip()
    if photo_file_id:
        payload: dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_file_id,
        }
        if cap:
            payload['caption'] = cap
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return call_method(platform, 'sendPhoto', settings=settings, json_body=payload)
    if photo_file is not None:
        data: dict[str, Any] = {'chat_id': str(chat_id)}
        if cap:
            data['caption'] = cap
        if reply_markup is not None:
            data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
        fname = photo_filename or getattr(photo_file, 'name', None) or 'photo.jpg'
        if isinstance(fname, str) and '/' in fname:
            fname = Path(fname).name
        files = {'photo': (fname, photo_file)}
        return call_method(platform, 'sendPhoto', settings=settings, data=data, files=files)
    if not photo_path or not photo_path.is_file():
        raise MessengerAPIError('مسیر عکس برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id)}
    if cap:
        data['caption'] = cap
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with photo_path.open('rb') as f:
        files = {'photo': (photo_path.name, f)}
        return call_method(platform, 'sendPhoto', settings=settings, data=data, files=files)


def send_video(
    platform: str,
    chat_id: int | str,
    *,
    settings: BotSettings | None = None,
    video_path: Path | None = None,
    video_file_id: str | None = None,
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if video_file_id:
        payload: dict[str, Any] = {
            'chat_id': chat_id,
            'video': video_file_id,
            'caption': caption,
        }
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return call_method(platform, 'sendVideo', settings=settings, json_body=payload)
    if not video_path or not video_path.is_file():
        raise MessengerAPIError('مسیر ویدیو برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with video_path.open('rb') as f:
        files = {'video': (video_path.name, f)}
        return call_method(platform, 'sendVideo', settings=settings, data=data, files=files)


def send_voice(
    platform: str,
    chat_id: int | str,
    *,
    settings: BotSettings | None = None,
    voice_path: Path | None = None,
    voice_file_id: str | None = None,
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if voice_file_id:
        payload: dict[str, Any] = {
            'chat_id': chat_id,
            'voice': voice_file_id,
            'caption': caption,
        }
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return call_method(platform, 'sendVoice', settings=settings, json_body=payload)
    if not voice_path or not voice_path.is_file():
        raise MessengerAPIError('مسیر صدا برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with voice_path.open('rb') as f:
        files = {'voice': (voice_path.name, f)}
        return call_method(platform, 'sendVoice', settings=settings, data=data, files=files)


def send_document(
    platform: str,
    chat_id: int | str,
    *,
    settings: BotSettings | None = None,
    document_path: Path | None = None,
    document_file_id: str | None = None,
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if document_file_id:
        payload: dict[str, Any] = {
            'chat_id': chat_id,
            'document': document_file_id,
            'caption': caption,
        }
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return call_method(platform, 'sendDocument', settings=settings, json_body=payload)
    if not document_path or not document_path.is_file():
        raise MessengerAPIError('مسیر سند برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with document_path.open('rb') as f:
        files = {'document': (document_path.name, f)}
        return call_method(platform, 'sendDocument', settings=settings, data=data, files=files)


def edit_message_reply_markup(
    platform: str,
    chat_id: int | str,
    message_id: int,
    *,
    settings: BotSettings | None = None,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'chat_id': chat_id,
        'message_id': message_id,
    }
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return call_method(platform, 'editMessageReplyMarkup', settings=settings, json_body=payload)


def answer_callback_query(
    platform: str,
    callback_query_id: str,
    *,
    settings: BotSettings | None = None,
    text: str | None = None,
    show_alert: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'callback_query_id': callback_query_id,
        'show_alert': show_alert,
    }
    if text is not None:
        payload['text'] = text
    return call_method(platform, 'answerCallbackQuery', settings=settings, json_body=payload)


def get_file(platform: str, file_id: str, *, settings: BotSettings | None = None) -> dict[str, Any]:
    return call_method(platform, 'getFile', settings=settings, json_body={'file_id': file_id})


def file_download_url(platform: str, file_path: str, *, settings: BotSettings | None = None) -> str:
    cfg = _resolve_settings(platform, settings)
    token = (cfg.bot_token or '').strip()
    base = get_api_base(platform).rstrip('/')
    parts = [p for p in file_path.replace('\\', '/').split('/') if p]
    enc = '/'.join(quote(p, safe='') for p in parts)
    return f'{base}/file/bot{token}/{enc}'


def download_file_to_path(
    platform: str,
    file_id: str,
    dest: Path,
    *,
    settings: BotSettings | None = None,
) -> Path:
    """getFile + دانلود باینری به مسیر."""
    info = get_file(platform, file_id, settings=settings)
    fobj = info.get('result') or {}
    path = fobj.get('file_path')
    if not path:
        raise MessengerAPIError('file_path در پاسخ getFile نیست.')
    url = file_download_url(platform, path, settings=settings)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def set_webhook(platform: str, url: str, *, settings: BotSettings | None = None) -> dict[str, Any]:
    return call_method(platform, 'setWebhook', settings=settings, json_body={'url': url})


def delete_webhook(platform: str, *, settings: BotSettings | None = None) -> dict[str, Any]:
    return call_method(platform, 'deleteWebhook', settings=settings, json_body={})


def get_webhook_info(platform: str, *, settings: BotSettings | None = None) -> dict[str, Any]:
    return call_method(platform, 'getWebhookInfo', settings=settings)


def create_invoice_link(
    platform: str,
    invoice: dict[str, Any],
    *,
    settings: BotSettings | None = None,
) -> dict[str, Any]:
    return call_method(platform, 'createInvoiceLink', settings=settings, json_body=invoice)


def answer_pre_checkout_query(
    platform: str,
    pre_checkout_query_id: str,
    *,
    ok: bool = True,
    error_message: str | None = None,
    settings: BotSettings | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'pre_checkout_query_id': pre_checkout_query_id,
        'ok': ok,
    }
    if not ok and error_message:
        payload['error_message'] = error_message
    return call_method(platform, 'answerPreCheckoutQuery', settings=settings, json_body=payload)


def sleep_after_rate_limit(payload: dict[str, Any]) -> None:
    """اگر پاسخ خطا شامل retry_after بود، همان‌قدر صبر کن."""
    params = payload.get('parameters') or {}
    retry = params.get('retry_after')
    if retry is not None:
        time.sleep(float(retry))
