from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MetaErrorCategory(str, Enum):
    RETRYABLE = 'retryable'
    NON_RETRYABLE = 'non_retryable'
    AUTHENTICATION = 'authentication'
    PERMISSION = 'permission'
    RATE_LIMIT = 'rate_limit'
    VALIDATION = 'validation'
    UNSUPPORTED = 'unsupported_feature'
    EXPIRED_WINDOW = 'expired_interaction_window'
    DELETED_CONTENT = 'deleted_content'
    DISCONNECTED = 'disconnected_account'


@dataclass
class MetaAPIError(Exception):
    category: MetaErrorCategory
    internal_code: str
    message_fa: str
    http_status: int = 0
    meta_code: int | None = None
    meta_subcode: int | None = None
    retry_after: float | None = None

    def __str__(self) -> str:
        return f'{self.internal_code}: {self.message_fa}'


_FA_MESSAGES = {
    MetaErrorCategory.AUTHENTICATION: 'احراز هویت Meta ناموفق بود. حساب را دوباره متصل کنید.',
    MetaErrorCategory.PERMISSION: 'مجوز لازم از Meta در دسترس نیست. حساب را دوباره متصل کن یا تنظیمات مجوز را بررسی کن.',
    MetaErrorCategory.RATE_LIMIT: 'محدودیت نرخ Meta فعال است. کمی بعد دوباره تلاش می‌شود.',
    MetaErrorCategory.VALIDATION: 'درخواست ارسال‌شده معتبر نبود.',
    MetaErrorCategory.UNSUPPORTED: 'این قابلیت توسط API رسمی Meta پشتیبانی نمی‌شود یا نیازمند تأیید است.',
    MetaErrorCategory.EXPIRED_WINDOW: 'پنجرهٔ تعامل پیام منقضی شده است.',
    MetaErrorCategory.DELETED_CONTENT: 'محتوای مرتبط حذف یا نامعتبر است.',
    MetaErrorCategory.DISCONNECTED: 'اتصال حساب اینستاگرام قطع است.',
    MetaErrorCategory.RETRYABLE: 'خطای موقتی Meta. دوباره تلاش می‌شود.',
    MetaErrorCategory.NON_RETRYABLE: 'عملیات قابل انجام نیست.',
}


def map_meta_error(
    *,
    http_status: int = 0,
    body: dict | None = None,
    retry_after: float | None = None,
) -> MetaAPIError:
    body = body or {}
    err = body.get('error') if isinstance(body.get('error'), dict) else body
    code = err.get('code') if isinstance(err, dict) else None
    subcode = err.get('error_subcode') if isinstance(err, dict) else None

    if http_status == 429 or code in (4, 17, 32, 613):
        cat = MetaErrorCategory.RATE_LIMIT
    elif code in (10, 200, 294):
        cat = MetaErrorCategory.PERMISSION
    elif http_status in (401,) or code in (190, 102):
        cat = MetaErrorCategory.AUTHENTICATION
    elif http_status == 403 and code not in (10, 200, 294):
        cat = MetaErrorCategory.AUTHENTICATION
    elif code in (100,) or http_status == 400:
        cat = MetaErrorCategory.VALIDATION
    elif code in (551,):
        cat = MetaErrorCategory.EXPIRED_WINDOW
    elif http_status >= 500:
        cat = MetaErrorCategory.RETRYABLE
    else:
        cat = MetaErrorCategory.NON_RETRYABLE

    internal = f'META_{cat.value.upper()}_{code or http_status}'
    return MetaAPIError(
        category=cat,
        internal_code=internal,
        message_fa=_FA_MESSAGES.get(cat, _FA_MESSAGES[MetaErrorCategory.NON_RETRYABLE]),
        http_status=http_status,
        meta_code=code if isinstance(code, int) else None,
        meta_subcode=subcode if isinstance(subcode, int) else None,
        retry_after=retry_after,
    )


class MetaGraphClient:
    """کلاینت مرکزی Graph API — توکن فقط اینجا decrypt می‌شود."""

    def __init__(
        self,
        *,
        access_token: str,
        api_version: str | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        session: requests.Session | None = None,
        host: str = 'graph.facebook.com',
    ):
        self.access_token = access_token
        self.api_version = (
            api_version
            or getattr(settings, 'INSTAGRAM_GRAPH_API_VERSION', '')
        )
        if not self.api_version:
            raise ValueError('INSTAGRAM_GRAPH_API_VERSION is required')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.host = host
        self.base = f'https://{host}/{self.api_version}/'

    def _url(self, path: str) -> str:
        return urljoin(self.base, path.lstrip('/'))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        correlation_id: str = '',
    ) -> dict[str, Any]:
        params = dict(params or {})
        params['access_token'] = self.access_token
        last_error: MetaAPIError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.request(
                    method.upper(),
                    self._url(path),
                    params=params if method.upper() == 'GET' else {'access_token': self.access_token},
                    json=json_body if method.upper() != 'GET' else None,
                    data=None if method.upper() == 'GET' or json_body else params,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = MetaAPIError(
                    category=MetaErrorCategory.RETRYABLE,
                    internal_code='META_NETWORK',
                    message_fa='ارتباط با Meta برقرار نشد.',
                )
                logger.warning(
                    'Meta network error cid=%s attempt=%s: %s',
                    correlation_id,
                    attempt,
                    type(exc).__name__,
                )
                time.sleep(min(2 ** attempt, 8) + (0.1 * attempt))
                continue

            retry_after = None
            if resp.headers.get('Retry-After'):
                try:
                    retry_after = float(resp.headers['Retry-After'])
                except ValueError:
                    retry_after = None

            try:
                body = resp.json() if resp.content else {}
            except ValueError:
                body = {}

            if 200 <= resp.status_code < 300:
                return body if isinstance(body, dict) else {'data': body}

            err = map_meta_error(
                http_status=resp.status_code,
                body=body if isinstance(body, dict) else {},
                retry_after=retry_after,
            )
            last_error = err
            logger.warning(
                'Meta API error cid=%s code=%s cat=%s status=%s',
                correlation_id,
                err.internal_code,
                err.category,
                resp.status_code,
            )
            if err.category in (
                MetaErrorCategory.RETRYABLE,
                MetaErrorCategory.RATE_LIMIT,
            ) and attempt < self.max_retries:
                delay = err.retry_after or min(2 ** attempt, 16)
                time.sleep(delay)
                continue
            raise err

        assert last_error is not None
        raise last_error

    def get(self, path: str, **kwargs) -> dict[str, Any]:
        return self.request('GET', path, **kwargs)

    def post(self, path: str, **kwargs) -> dict[str, Any]:
        return self.request('POST', path, **kwargs)

    def delete(self, path: str, **kwargs) -> dict[str, Any]:
        return self.request('DELETE', path, **kwargs)

    def debug_token(self, input_token: str) -> dict[str, Any]:
        app_token = f"{settings.META_APP_ID}|{settings.META_APP_SECRET}"
        return self.request(
            'GET',
            'debug_token',
            params={'input_token': input_token, 'access_token': app_token},
        )

    def get_ig_user(self, ig_user_id: str) -> dict[str, Any]:
        return self.get(
            ig_user_id,
            params={'fields': 'id,username,name,profile_picture_url'},
        )

    def send_text_message(
        self,
        *,
        ig_user_id: str,
        recipient_id: str,
        text: str,
        correlation_id: str = '',
    ) -> dict[str, Any]:
        return self.post(
            f'{ig_user_id}/messages',
            json_body={
                'recipient': {'id': recipient_id},
                'message': {'text': text[:1000]},
            },
            correlation_id=correlation_id,
        )

    def subscribe_webhooks(self, ig_user_id: str, fields: list[str]) -> dict[str, Any]:
        return self.post(
            f'{ig_user_id}/subscribed_apps',
            params={'subscribed_fields': ','.join(fields)},
        )

    def get_webhook_subscriptions(self, ig_user_id: str) -> dict[str, Any]:
        return self.get(f'{ig_user_id}/subscribed_apps')

    def list_media(self, ig_user_id: str) -> dict[str, Any]:
        return self.get(
            f'{ig_user_id}/media',
            params={
                'fields': (
                    'id,caption,media_type,media_product_type,media_url,'
                    'thumbnail_url,permalink,timestamp'
                ),
                'limit': 100,
            },
        )

    def list_stories(self, ig_user_id: str) -> dict[str, Any]:
        return self.get(
            f'{ig_user_id}/stories',
            params={
                'fields': (
                    'id,caption,media_type,media_product_type,media_url,'
                    'thumbnail_url,permalink,timestamp'
                ),
                'limit': 100,
            },
        )

    def reply_to_comment(
        self,
        *,
        comment_id: str,
        message: str,
        correlation_id: str = '',
    ) -> dict[str, Any]:
        return self.post(
            f'{comment_id}/replies',
            json_body={'message': message[:1000]},
            correlation_id=correlation_id,
        )

    def private_reply_to_comment(
        self,
        *,
        page_id: str,
        comment_id: str,
        message: str,
        correlation_id: str = '',
    ) -> dict[str, Any]:
        """Private Reply در محدودهٔ رسمی Meta — یک‌بار در پنجره مجاز."""
        return self.post(
            f'{page_id}/messages',
            json_body={
                'recipient': {'comment_id': comment_id},
                'message': {'text': message[:1000]},
            },
            correlation_id=correlation_id,
        )
