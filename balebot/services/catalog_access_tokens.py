"""صدور و اعتبارسنجی توکن دسترسی به فایل‌های محتوا."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import quote, urlencode

from django.conf import settings

TOKEN_TTL_SECONDS = 24 * 60 * 60


def _signing_key() -> bytes:
    return (settings.SECRET_KEY or 'catalog-media').encode('utf-8')


def issue_media_token(*, subscriber_id: int, media_id: int, ttl: int = TOKEN_TTL_SECONDS) -> str:
    expires = int(time.time()) + ttl
    payload = f'{subscriber_id}:{media_id}:{expires}'
    sig = hmac.new(_signing_key(), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f'{payload}:{sig}'


def verify_media_token(token: str, *, subscriber_id: int, media_id: int) -> bool:
    if not token:
        return False
    parts = token.split(':')
    if len(parts) != 4:
        return False
    try:
        token_sub = int(parts[0])
        token_media = int(parts[1])
        expires = int(parts[2])
    except ValueError:
        return False
    if token_sub != subscriber_id or token_media != media_id:
        return False
    if expires < int(time.time()):
        return False
    payload = f'{parts[0]}:{parts[1]}:{parts[2]}'
    expected = hmac.new(_signing_key(), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts[3])


def append_media_token(url: str, token: str) -> str:
    if not url or not token:
        return url
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}{urlencode({"access_token": token})}'
