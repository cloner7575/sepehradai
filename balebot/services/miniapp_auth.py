"""اعتبارسنجی initData مینی‌اپ بله و تلگرام."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from balebot.models import BotSettings, Platform

MAX_AUTH_AGE_SECONDS = 86400


def _build_data_check_string(pairs: list[tuple[str, str]]) -> str:
    filtered = [(k, v) for k, v in pairs if k != 'hash']
    filtered.sort(key=lambda x: x[0])
    return '\n'.join(f'{k}={v}' for k, v in filtered)


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = MAX_AUTH_AGE_SECONDS,
) -> dict[str, Any] | None:
    """برگرداندن داده پارس‌شده در صورت معتبر بودن؛ در غیر این صورت None."""
    raw = (init_data or '').strip()
    token = (bot_token or '').strip()
    if not raw or not token:
        return None

    pairs = parse_qsl(raw, keep_blank_values=True)
    data = dict(pairs)
    received_hash = data.get('hash', '')
    if not received_hash:
        return None

    check_string = _build_data_check_string(pairs)
    secret_key = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        return None

    auth_date = int(data.get('auth_date') or 0)
    if auth_date and time.time() - auth_date > max_age_seconds:
        return None

    user_raw = data.get('user')
    user: dict[str, Any] | None = None
    if user_raw:
        try:
            user = json.loads(user_raw)
        except json.JSONDecodeError:
            return None

    return {
        'query_id': data.get('query_id', ''),
        'auth_date': auth_date,
        'user': user,
    }


def validate_for_bot_settings(init_data: str, cfg: BotSettings) -> dict[str, Any] | None:
    return validate_init_data(init_data, cfg.bot_token or '')


def get_webapp_secret_label(platform: str) -> str:
    return 'WebAppData'
