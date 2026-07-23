from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _derive_fernet_key(raw: str) -> bytes:
    """کلید Fernet از env — اگر url-safe 32-byte نباشد، از SHA256 مشتق می‌شود."""
    raw = (raw or '').strip()
    if not raw:
        if not getattr(settings, 'DEBUG', False):
            raise ImproperlyConfigured('META_TOKEN_ENCRYPTION_KEY is required in production')
        raw = getattr(settings, 'SECRET_KEY', '') or 'dev-insecure-ig-token-key'
    try:
        decoded = base64.urlsafe_b64decode(raw.encode('ascii'))
        if len(decoded) == 32:
            return raw.encode('ascii')
    except Exception:
        pass
    digest = hashlib.sha256(raw.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    key = getattr(settings, 'META_TOKEN_ENCRYPTION_KEY', '') or ''
    return Fernet(_derive_fernet_key(key))


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return ''
    return get_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_token(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    try:
        return get_fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except InvalidToken:
        logger.error('Instagram token decrypt failed')
        raise


def redact_token(token: str) -> str:
    if not token or len(token) < 8:
        return '***'
    return f'{token[:4]}…{token[-4:]}'
