"""کلاینت HTTP برای API بازوی بله (سازگار با Bot API)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings


class BaleAPIError(Exception):
    def __init__(self, message: str, error_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.payload = payload or {}


def _bot_base_url() -> str:
    token = getattr(settings, 'BALE_BOT_TOKEN', '') or ''
    if not token.strip():
        raise BaleAPIError('BALE_BOT_TOKEN تنظیم نشده است.')
    base = getattr(settings, 'BALE_API_BASE', 'https://tapi.bale.ai').rstrip('/')
    return f'{base}/bot{token}/'


def call_method(
    method: str,
    *,
    json_body: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """فراخوانی متد API؛ در خطای منطقی BaleAPIError می‌اندازد."""
    url = urljoin(_bot_base_url(), method)
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
        raise BaleAPIError(f'خطای شبکه: {e}') from e

    try:
        body = r.json()
    except json.JSONDecodeError as e:
        raise BaleAPIError(f'پاسخ نامعتبر HTTP {r.status_code}: {r.text[:500]}') from e

    if not body.get('ok'):
        raise BaleAPIError(
            body.get('description') or 'خطای نامشخص API',
            error_code=body.get('error_code'),
            payload=body,
        )
    return body


def get_me() -> dict[str, Any]:
    return call_method('getMe')


def send_message(
    chat_id: int | str,
    text: str,
    *,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {'chat_id': chat_id, 'text': text}
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return call_method('sendMessage', json_body=payload)


def send_photo(
    chat_id: int | str,
    *,
    photo_path: Path | None = None,
    photo_file_id: str | None = None,
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if photo_file_id:
        payload: dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_file_id,
            'caption': caption,
        }
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        return call_method('sendPhoto', json_body=payload)
    if not photo_path or not photo_path.is_file():
        raise BaleAPIError('مسیر عکس برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with photo_path.open('rb') as f:
        files = {'photo': (photo_path.name, f)}
        return call_method('sendPhoto', data=data, files=files)


def send_video(
    chat_id: int | str,
    *,
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
        return call_method('sendVideo', json_body=payload)
    if not video_path or not video_path.is_file():
        raise BaleAPIError('مسیر ویدیو برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with video_path.open('rb') as f:
        files = {'video': (video_path.name, f)}
        return call_method('sendVideo', data=data, files=files)


def send_voice(
    chat_id: int | str,
    *,
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
        return call_method('sendVoice', json_body=payload)
    if not voice_path or not voice_path.is_file():
        raise BaleAPIError('مسیر صدا برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with voice_path.open('rb') as f:
        files = {'voice': (voice_path.name, f)}
        return call_method('sendVoice', data=data, files=files)


def send_document(
    chat_id: int | str,
    *,
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
        return call_method('sendDocument', json_body=payload)
    if not document_path or not document_path.is_file():
        raise BaleAPIError('مسیر سند برای ارسال نامعتبر است.')
    data = {'chat_id': str(chat_id), 'caption': caption}
    if reply_markup is not None:
        data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    with document_path.open('rb') as f:
        files = {'document': (document_path.name, f)}
        return call_method('sendDocument', data=data, files=files)


def edit_message_reply_markup(
    chat_id: int | str,
    message_id: int,
    *,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'chat_id': chat_id,
        'message_id': message_id,
    }
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return call_method('editMessageReplyMarkup', json_body=payload)


def answer_callback_query(
    callback_query_id: str,
    *,
    text: str | None = None,
    show_alert: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'callback_query_id': callback_query_id,
        'show_alert': show_alert,
    }
    if text is not None:
        payload['text'] = text
    return call_method('answerCallbackQuery', json_body=payload)


def get_file(file_id: str) -> dict[str, Any]:
    return call_method('getFile', json_body={'file_id': file_id})


def file_download_url(file_path: str) -> str:
    token = settings.BALE_BOT_TOKEN
    base = settings.BALE_API_BASE.rstrip('/')
    from urllib.parse import quote

    parts = [p for p in file_path.replace('\\', '/').split('/') if p]
    enc = '/'.join(quote(p, safe='') for p in parts)
    return f'{base}/file/bot{token}/{enc}'


def download_file_to_path(file_id: str, dest: Path) -> Path:
    """getFile + دانلود باینری به مسیر."""
    info = get_file(file_id)
    fobj = info.get('result') or {}
    path = fobj.get('file_path')
    if not path:
        raise BaleAPIError('file_path در پاسخ getFile نیست.')
    url = file_download_url(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def set_webhook(url: str) -> dict[str, Any]:
    return call_method('setWebhook', json_body={'url': url})


def delete_webhook() -> dict[str, Any]:
    return call_method('deleteWebhook', json_body={})


def sleep_after_rate_limit(payload: dict[str, Any]) -> None:
    """اگر پاسخ خطا شامل retry_after بود، همان‌قدر صبر کن."""
    params = payload.get('parameters') or {}
    retry = params.get('retry_after')
    if retry is not None:
        time.sleep(float(retry))
