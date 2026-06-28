"""اکسپورت و ایمپورت JSON الگوهای آماده فروشگاه (فقط سوپرادمین)."""

from __future__ import annotations

import json
import re
from typing import Any

from django.db import transaction
from django.utils.text import slugify

from balebot.models import StoreTemplate

EXPORT_VERSION = 1
_BUNDLE_KIND = 'store_templates'
_SINGLE_KIND = 'store_template'
_SLUG_RE = re.compile(r'^[-a-z0-9]+$')
_MAX_SLUG_LEN = 80
_MAX_NAME_LEN = 120
_MAX_INDUSTRY_LEN = 60
_MAX_DESC_LEN = 255


class StoreTemplateImportError(Exception):
    """خطای اعتبارسنجی فایل ایمپورت."""


def template_to_export_dict(template: StoreTemplate) -> dict[str, Any]:
    return {
        'slug': template.slug,
        'name': template.name,
        'industry': template.industry,
        'description': template.description or '',
        'sort_order': template.sort_order,
        'is_active': template.is_active,
        'data': template.data if isinstance(template.data, dict) else {},
    }


def build_export_bundle(templates) -> dict[str, Any]:
    rows = [template_to_export_dict(t) for t in templates]
    return {
        'version': EXPORT_VERSION,
        'kind': _BUNDLE_KIND,
        'templates': rows,
    }


def build_single_export(template: StoreTemplate) -> dict[str, Any]:
    return {
        'version': EXPORT_VERSION,
        'kind': _SINGLE_KIND,
        'template': template_to_export_dict(template),
    }


def _normalize_slug(raw: str) -> str:
    slug = slugify((raw or '').strip(), allow_unicode=False)[:_MAX_SLUG_LEN]
    if not slug or not _SLUG_RE.match(slug):
        raise StoreTemplateImportError(f'شناسه نامعتبر: {raw!r}')
    return slug


def _normalize_import_row(raw: Any, *, index: int | None = None) -> dict[str, Any]:
    label = f'الگوی {index}' if index is not None else 'الگو'
    if not isinstance(raw, dict):
        raise StoreTemplateImportError(f'{label}: ساختار نامعتبر است.')

    slug = _normalize_slug(str(raw.get('slug') or ''))
    name = (str(raw.get('name') or '')).strip()[:_MAX_NAME_LEN]
    if not name:
        raise StoreTemplateImportError(f'{label} ({slug}): نام الزامی است.')

    industry = (str(raw.get('industry') or 'general')).strip()[:_MAX_INDUSTRY_LEN] or 'general'
    description = (str(raw.get('description') or '')).strip()[:_MAX_DESC_LEN]

    data = raw.get('data')
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise StoreTemplateImportError(f'{label} ({slug}): فیلد data باید شیء JSON باشد.')

    sort_order_raw = raw.get('sort_order', 0)
    try:
        sort_order = int(sort_order_raw)
    except (TypeError, ValueError) as exc:
        raise StoreTemplateImportError(
            f'{label} ({slug}): sort_order باید عدد باشد.',
        ) from exc

    is_active = raw.get('is_active', True)
    if not isinstance(is_active, bool):
        is_active = str(is_active).strip().lower() not in ('0', 'false', 'no', 'off')

    return {
        'slug': slug,
        'name': name,
        'industry': industry,
        'description': description,
        'sort_order': sort_order,
        'is_active': is_active,
        'data': data,
    }


def parse_import_payload(raw: Any) -> list[dict[str, Any]]:
    """JSON بارگذاری‌شده را به لیست ردیف‌های قابل ایمپورت تبدیل می‌کند."""
    if isinstance(raw, list):
        source = raw
    elif isinstance(raw, dict):
        kind = (raw.get('kind') or '').strip()
        if kind == _SINGLE_KIND and isinstance(raw.get('template'), dict):
            source = [raw['template']]
        elif isinstance(raw.get('templates'), list):
            source = raw['templates']
        elif raw.get('slug'):
            source = [raw]
        else:
            raise StoreTemplateImportError(
                'فرمت JSON نامعتبر است. فیلد templates یا template لازم است.',
            )
    else:
        raise StoreTemplateImportError('فایل باید JSON معتبر باشد.')

    if not source:
        raise StoreTemplateImportError('هیچ الگویی در فایل یافت نشد.')

    return [_normalize_import_row(row, index=i + 1) for i, row in enumerate(source)]


def parse_import_file(content: bytes | str) -> list[dict[str, Any]]:
    text = content.decode('utf-8-sig') if isinstance(content, bytes) else content
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StoreTemplateImportError(f'JSON نامعتبر: {exc}') from exc
    return parse_import_payload(payload)


@transaction.atomic
def import_store_templates(
    rows: list[dict[str, Any]],
    *,
    deactivate_missing: bool = False,
) -> dict[str, int]:
    stats = {'created': 0, 'updated': 0, 'deactivated': 0}
    slugs: set[str] = set()

    for row in rows:
        slug = row['slug']
        slugs.add(slug)
        defaults = {
            'name': row['name'],
            'industry': row['industry'],
            'description': row['description'],
            'sort_order': row['sort_order'],
            'is_active': row['is_active'],
            'data': row['data'],
        }
        _obj, created = StoreTemplate.objects.update_or_create(
            slug=slug,
            defaults=defaults,
        )
        if created:
            stats['created'] += 1
        else:
            stats['updated'] += 1

    if deactivate_missing:
        stats['deactivated'] = (
            StoreTemplate.objects.exclude(slug__in=slugs).filter(is_active=True).update(is_active=False)
        )

    return stats


def delete_store_template(slug: str) -> str:
    template = StoreTemplate.objects.filter(slug=slug).first()
    if template is None:
        raise StoreTemplateImportError('الگو یافت نشد.')
    name = template.name
    template.delete()
    return name


def delete_all_store_templates(*, include_inactive: bool = False) -> int:
    qs = StoreTemplate.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    count, _ = qs.delete()
    return int(count)
