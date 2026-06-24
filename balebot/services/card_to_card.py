"""پرداخت کارت‌به‌کارت — نمایش اطلاعات و اعتبارسنجی."""

from __future__ import annotations

import re

from balebot.models import CatalogSettings


def _card_digits(value: str) -> str:
    return ''.join(ch for ch in (value or '') if ch.isdigit())


def _sheba_normalized(value: str) -> str:
    raw = (value or '').upper().replace(' ', '').replace('-', '')
    if raw.startswith('IR'):
        return raw[:26]
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if len(digits) == 24:
        return f'IR{digits}'
    return raw


def format_card_display(number: str) -> str:
    digits = _card_digits(number)
    if not digits:
        return ''
    return '-'.join(digits[i : i + 4] for i in range(0, len(digits), 4))


def format_sheba_display(sheba: str) -> str:
    normalized = _sheba_normalized(sheba)
    if not normalized:
        return ''
    if normalized.startswith('IR') and len(normalized) >= 26:
        body = normalized[2:26]
        return f'IR{body[0:2]} {body[2:6]} {body[6:10]} {body[10:14]} {body[14:18]} {body[18:22]} {body[22:24]}'
    return normalized


def payment_card_to_card_ready(catalog: CatalogSettings) -> bool:
    if not catalog.payment_card_to_card_enabled:
        return False
    card = _card_digits(catalog.card_to_card_number)
    sheba = _sheba_normalized(catalog.card_to_card_sheba)
    holder = (catalog.card_to_card_holder or '').strip()
    return len(card) >= 16 and sheba.startswith('IR') and len(sheba) == 26 and bool(holder)


def build_card_to_card_payload(catalog: CatalogSettings) -> dict[str, str]:
    number = _card_digits(catalog.card_to_card_number)
    sheba = _sheba_normalized(catalog.card_to_card_sheba)
    holder = (catalog.card_to_card_holder or '').strip()
    return {
        'number': number,
        'number_display': format_card_display(number),
        'sheba': sheba,
        'sheba_display': format_sheba_display(sheba),
        'holder': holder,
    }


def validate_sheba(value: str) -> bool:
    sheba = _sheba_normalized(value)
    return bool(re.fullmatch(r'IR\d{24}', sheba))
