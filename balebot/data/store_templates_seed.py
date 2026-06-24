"""دادهٔ الگوهای آماده فروشگاه — از فایل JSON بارگذاری می‌شود."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from balebot.data.home_blocks_presets import build_home_blocks_for_template
from balebot.data.start_flow_presets import upgrade_start_flow

_DATA_FILE = Path(__file__).with_name('store_templates.json')


def _enrich_sample_items(items: list) -> list:
    """compare_at_price و sales_count نمونه برای کاروسل تخفیف/پرفروش."""
    out: list = []
    for index, row in enumerate(items):
        if not isinstance(row, dict):
            continue
        item = copy.deepcopy(row)
        price = item.get('price')
        if index == 0 and price not in (None, '', 0) and not item.get('compare_at_price'):
            try:
                p = int(price)
                if p > 0:
                    item['compare_at_price'] = int(p * 1.12)
                    item['is_featured'] = True
            except (TypeError, ValueError):
                pass
        if index == 0 and not item.get('sales_count'):
            item['sales_count'] = 24
        elif index == 1 and not item.get('sales_count'):
            item['sales_count'] = 12
        out.append(item)
    return out


def _enrich_template_data(row: dict) -> dict:
    """home_blocks، start_flow و نمونه‌محصولات را با قابلیت‌های جدید غنی می‌کند."""
    data = copy.deepcopy(row.get('data') or {})
    settings = data.setdefault('settings', {})
    marketing = data.get('marketing') if isinstance(data.get('marketing'), dict) else {}
    categories = data.get('categories') if isinstance(data.get('categories'), list) else []
    slug = row.get('slug') or ''
    industry = row.get('industry') or 'general'

    if not settings.get('home_blocks'):
        settings['home_blocks'] = build_home_blocks_for_template(
            slug=slug,
            industry=industry,
            categories=categories,
            marketing=marketing,
            settings=settings,
        )

    start_flow = data.get('start_flow')
    if isinstance(start_flow, dict) and start_flow.get('root'):
        data['start_flow'] = upgrade_start_flow(
            start_flow,
            slug=slug,
            industry=industry,
            marketing=marketing,
        )

    if isinstance(data.get('items'), list):
        data['items'] = _enrich_sample_items(data['items'])

    return data


def load_store_templates() -> list[dict]:
    with _DATA_FILE.open(encoding='utf-8') as handle:
        payload = json.load(handle)
    templates: list[dict] = []
    for index, row in enumerate(payload.get('templates') or [], start=1):
        if not isinstance(row, dict) or not row.get('slug'):
            continue
        templates.append({
            'slug': row['slug'],
            'name': row['name'],
            'industry': row.get('industry') or 'general',
            'description': (row.get('description') or '')[:255],
            'sort_order': index,
            'data': _enrich_template_data(row),
        })
    return templates


STORE_TEMPLATES = load_store_templates()
