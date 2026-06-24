"""دادهٔ الگوهای آماده فروشگاه — از فایل JSON بارگذاری می‌شود."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).with_name('store_templates.json')


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
            'data': row.get('data') or {},
        })
    return templates


STORE_TEMPLATES = load_store_templates()
