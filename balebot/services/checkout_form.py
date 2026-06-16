"""فرم قابل تنظیم اطلاعات کاربر هنگام ثبت سفارش مینی‌اپ."""

from __future__ import annotations

import json
import re
from typing import Any

FIELD_TYPES = frozenset({'text', 'tel', 'email', 'textarea'})

DEFAULT_CHECKOUT_FIELDS: list[dict[str, Any]] = [
    {
        'key': 'full_name',
        'label': 'نام و نام خانوادگی',
        'type': 'text',
        'required': True,
        'enabled': True,
    },
    {
        'key': 'phone',
        'label': 'شماره تماس',
        'type': 'tel',
        'required': True,
        'enabled': True,
    },
    {
        'key': 'email',
        'label': 'ایمیل',
        'type': 'email',
        'required': False,
        'enabled': False,
    },
    {
        'key': 'address',
        'label': 'آدرس',
        'type': 'textarea',
        'required': True,
        'enabled': True,
    },
    {
        'key': 'city',
        'label': 'شهر',
        'type': 'text',
        'required': False,
        'enabled': False,
    },
    {
        'key': 'postal_code',
        'label': 'کد پستی',
        'type': 'text',
        'required': False,
        'enabled': False,
    },
    {
        'key': 'note',
        'label': 'توضیحات',
        'type': 'textarea',
        'required': False,
        'enabled': False,
    },
]


def default_checkout_form() -> dict[str, Any]:
    return {
        'enabled': True,
        'title': 'اطلاعات تحویل',
        'fields': [dict(f) for f in DEFAULT_CHECKOUT_FIELDS],
    }


def _normalize_key(raw: str) -> str:
    key = re.sub(r'[^a-z0-9_]', '_', (raw or '').strip().lower())
    key = re.sub(r'_+', '_', key).strip('_')
    return key[:64]


def _normalize_field(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    key = _normalize_key(str(raw.get('key') or ''))
    label = str(raw.get('label') or '').strip()[:120]
    if not key or not label:
        return None
    field_type = str(raw.get('type') or 'text').strip().lower()
    if field_type not in FIELD_TYPES:
        field_type = 'text'
    return {
        'key': key,
        'label': label,
        'type': field_type,
        'required': bool(raw.get('required')),
        'enabled': bool(raw.get('enabled')),
    }


def sanitize_checkout_form(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return default_checkout_form()
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return default_checkout_form()
    if not isinstance(raw, dict):
        return default_checkout_form()

    defaults = default_checkout_form()
    title = str(raw.get('title') or defaults['title']).strip()[:120] or defaults['title']
    enabled = bool(raw.get('enabled', defaults['enabled']))

    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw.get('fields') or []:
        field = _normalize_field(item)
        if not field or field['key'] in seen:
            continue
        seen.add(field['key'])
        fields.append(field)

    if not fields:
        fields = [dict(f) for f in DEFAULT_CHECKOUT_FIELDS]

    return {
        'enabled': enabled,
        'title': title,
        'fields': fields,
    }


def get_checkout_form(raw: Any) -> dict[str, Any]:
    return sanitize_checkout_form(raw)


def enabled_checkout_fields(form: dict[str, Any]) -> list[dict[str, Any]]:
    if not form.get('enabled'):
        return []
    return [f for f in form.get('fields') or [] if f.get('enabled')]


def public_checkout_form(raw: Any) -> dict[str, Any]:
    form = get_checkout_form(raw)
    return {
        'enabled': bool(form.get('enabled')),
        'title': form.get('title') or 'اطلاعات تحویل',
        'fields': enabled_checkout_fields(form),
    }


def validate_customer_data(form_raw: Any, data: Any) -> tuple[dict[str, str], list[str]]:
    form = get_checkout_form(form_raw)
    fields = enabled_checkout_fields(form)
    if not fields:
        return {}, []

    if not isinstance(data, dict):
        data = {}

    result: dict[str, str] = {}
    errors: list[str] = []
    for field in fields:
        key = field['key']
        raw_value = data.get(key)
        value = str(raw_value or '').strip()
        if field.get('required') and not value:
            errors.append(f'{field["label"]} الزامی است.')
            continue
        if value and field.get('type') == 'email' and '@' not in value:
            errors.append(f'{field["label"]} معتبر نیست.')
            continue
        if value:
            result[key] = value[:2000]
    return result, errors


def format_customer_data_for_message(form_raw: Any, data: dict[str, Any]) -> str:
    if not data:
        return ''
    form = get_checkout_form(form_raw)
    labels = {f['key']: f['label'] for f in form.get('fields') or []}
    lines: list[str] = []
    for key, value in data.items():
        text = str(value or '').strip()
        if not text:
            continue
        label = labels.get(key, key)
        lines.append(f'{label}: {text}')
    return '\n'.join(lines)
