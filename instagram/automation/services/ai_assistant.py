"""لایه اختیاری AI — پیش‌فرض خاموش؛ بدون auto-send به مشتری."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from instagram.automation.services.feature_flags import feature_enabled

logger = logging.getLogger(__name__)


class AIProvider(Protocol):
    def complete(self, *, prompt: str, timeout: float = 15.0) -> str: ...


class NullAIProvider:
    def complete(self, *, prompt: str, timeout: float = 15.0) -> str:
        return ''


class EchoSuggestProvider:
    """Provider توسعه — پیشنهاد ساده بدون مدل خارجی."""

    def complete(self, *, prompt: str, timeout: float = 15.0) -> str:
        return 'پیشنهاد نمونه: لطفاً لینک فروشگاه را از پیام‌های قبلی بررسی کنید. (نیاز به تأیید کارشناس)'


def get_provider() -> AIProvider:
    return NullAIProvider()


def redact_pii(text: str) -> str:
    import re

    text = re.sub(r'09\d{9}', '[PHONE]', text or '')
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '[EMAIL]', text)
    return text


def suggest_reply(*, workspace, conversation, messages: list[str]) -> dict[str, Any]:
    return {'ok': False, 'error': 'feature_disabled', 'suggestion': ''}


def classify_intent(*, workspace, text: str) -> dict[str, Any]:
    if not feature_enabled(workspace, 'instagram_ai_assistant'):
        return {'ok': False, 'intent': 'unknown'}
    t = (text or '').lower()
    if 'قیمت' in t or 'price' in t:
        intent = 'price_inquiry'
    elif 'سفارش' in t or 'order' in t:
        intent = 'order_status'
    elif 'سلام' in t:
        intent = 'greeting'
    else:
        intent = 'general'
    return {'ok': True, 'intent': intent, 'requires_review': True}
