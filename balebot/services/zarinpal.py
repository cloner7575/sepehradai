"""کلاینت REST API زرین‌پال (v4)."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

SANDBOX_BASE = 'https://sandbox.zarinpal.com/pg/v4/payment'
PRODUCTION_BASE = 'https://api.zarinpal.com/pg/v4/payment'
SANDBOX_START = 'https://sandbox.zarinpal.com/pg/StartPay/'
PRODUCTION_START = 'https://www.zarinpal.com/pg/StartPay/'


class ZarinpalError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def _api_base(sandbox: bool) -> str:
    return SANDBOX_BASE if sandbox else PRODUCTION_BASE


def _start_pay_base(sandbox: bool) -> str:
    return SANDBOX_START if sandbox else PRODUCTION_START


def request_payment(
    *,
    merchant_id: str,
    amount_rials: int,
    callback_url: str,
    description: str,
    sandbox: bool = True,
    metadata: dict[str, Any] | None = None,
) -> str:
    """درخواست پرداخت؛ authority برمی‌گرداند."""
    mid = (merchant_id or '').strip()
    if not mid:
        raise ZarinpalError('مرچنت‌آیدی زرین‌پال تنظیم نشده است.')
    if amount_rials <= 0:
        raise ZarinpalError('مبلغ پرداخت نامعتبر است.')

    payload: dict[str, Any] = {
        'merchant_id': mid,
        'amount': amount_rials,
        'callback_url': callback_url,
        'description': (description or 'پرداخت سفارش')[:255],
    }
    if metadata:
        payload['metadata'] = {k: str(v) for k, v in metadata.items()}

    url = f'{_api_base(sandbox)}/request.json'
    try:
        r = requests.post(url, json=payload, timeout=30)
        body = r.json()
    except requests.RequestException as e:
        raise ZarinpalError(f'خطای ارتباط با زرین‌پال: {e}') from e
    except ValueError as e:
        raise ZarinpalError('پاسخ نامعتبر از زرین‌پال') from e

    data = body.get('data') or {}
    errors = body.get('errors') or []
    if errors:
        err = errors[0] if isinstance(errors, list) else errors
        msg = err.get('message') if isinstance(err, dict) else str(err)
        code = err.get('code') if isinstance(err, dict) else None
        raise ZarinpalError(msg or 'خطای زرین‌پال', code=code)

    authority = (data.get('authority') or '').strip()
    code = data.get('code')
    if code != 100 or not authority:
        raise ZarinpalError('درخواست پرداخت زرین‌پال ناموفق بود.', code=code)
    return authority


def build_payment_url(authority: str, *, sandbox: bool = True) -> str:
    return f'{_start_pay_base(sandbox)}{authority}'


def verify_payment(
    *,
    merchant_id: str,
    authority: str,
    amount_rials: int,
    sandbox: bool = True,
) -> dict[str, Any]:
    mid = (merchant_id or '').strip()
    auth = (authority or '').strip()
    if not mid or not auth:
        raise ZarinpalError('اطلاعات تأیید پرداخت ناقص است.')

    url = f'{_api_base(sandbox)}/verify.json'
    payload = {
        'merchant_id': mid,
        'authority': auth,
        'amount': amount_rials,
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        body = r.json()
    except requests.RequestException as e:
        raise ZarinpalError(f'خطای ارتباط با زرین‌پال: {e}') from e
    except ValueError as e:
        raise ZarinpalError('پاسخ نامعتبر از زرین‌پال') from e

    data = body.get('data') or {}
    errors = body.get('errors') or []
    if errors:
        err = errors[0] if isinstance(errors, list) else errors
        msg = err.get('message') if isinstance(err, dict) else str(err)
        code = err.get('code') if isinstance(err, dict) else None
        raise ZarinpalError(msg or 'تأیید پرداخت ناموفق', code=code)

    code = data.get('code')
    if code not in (100, 101):
        raise ZarinpalError('پرداخت تأیید نشد.', code=code)
    return data
