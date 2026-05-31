"""اعتبارسنجی و نرمال‌سازی URL وب‌هوک قبل از setWebhook."""

from __future__ import annotations

import socket
from urllib.parse import urlparse

from balebot.models import Platform


def normalize_public_url(raw: str, *, platform: str) -> str:
    """فقط scheme + host (+ port) — بدون مسیر."""
    value = (raw or '').strip()
    if not value:
        return ''
    if not value.startswith(('http://', 'https://')):
        value = f'https://{value}'
    parsed = urlparse(value)
    if not parsed.netloc:
        return ''
    scheme = 'https' if platform == Platform.TELEGRAM else (parsed.scheme or 'https')
    if platform == Platform.TELEGRAM:
        scheme = 'https'
    netloc = parsed.netloc
    return f'{scheme}://{netloc}'.rstrip('/')


def check_hostname_resolves(hostname: str) -> tuple[bool, str]:
    host = (hostname or '').strip().lower()
    if not host:
        return False, 'نام میزبان (دامنه) خالی است.'
    if host in {'localhost', '127.0.0.1', '0.0.0.0', '::1'}:
        return False, 'آدرس localhost برای وب‌هوک تلگرام قابل استفاده نیست.'
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return False, (
            f'دامنه «{host}» از اینترنت resolve نمی‌شود ({exc}). '
            'DNS را در پنل Runflare/دامنه بررسی کنید یا چند دقیقه بعد دوباره تلاش کنید.'
        )
    return True, ''


def validate_webhook_url(url: str, *, platform: str) -> tuple[bool, str]:
    """بررسی URL کامل وب‌هوک قبل از فراخوانی API."""
    value = (url or '').strip()
    if not value:
        return False, 'آدرس وب‌هوک ساخته نشد. «آدرس عمومی سرور» و «رمز وب‌هوک» را پر کنید.'

    parsed = urlparse(value)
    if platform == Platform.TELEGRAM and parsed.scheme != 'https':
        return False, 'تلگرام فقط وب‌هوک HTTPS می‌پذیرد. آدرس عمومی را با https:// وارد کنید.'

    hostname = parsed.hostname
    if not hostname:
        return False, 'آدرس وب‌هوک نامعتبر است.'

    ok, msg = check_hostname_resolves(hostname)
    if not ok:
        return False, msg
    return True, ''


def explain_telegram_webhook_error(message: str) -> str:
    text = (message or '').strip()
    lower = text.lower()
    if 'failed to resolve host' in lower or 'name resolution' in lower:
        return (
            f'{text}\n'
            'سرورهای تلگرام نتوانستند دامنهٔ وب‌هوک را پیدا کنند. '
            'در تنظیمات تلگرام «آدرس عمومی سرور» را دقیقاً همان دامنهٔ HTTPS بگذارید '
            '(مثلاً https://sepehradbot.runflare.run)، بعد «ذخیره» و سپس «ثبت وب‌هوک» را بزنید.'
        )
    if 'https url must be provided' in lower:
        return f'{text}\nآدرس عمومی سرور باید با https:// شروع شود.'
    return text
