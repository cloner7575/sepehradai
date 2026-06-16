"""بلوک‌های صفحهٔ اصلی مینی‌اپ (سایت‌ساز گرافیکی)."""

from __future__ import annotations

import re
import uuid
from typing import Any

_BLOCK_ID_RE = re.compile(r'^b_[a-f0-9]{8}$')
_ALLOWED_TYPES = frozenset({
    'hero',
    'search',
    'slider',
    'categories',
    'featured',
    'products',
    'spacer',
})


def _new_block_id() -> str:
    return f'b_{uuid.uuid4().hex[:8]}'


def _ensure_block_id(raw: str | None) -> str:
    if raw and _BLOCK_ID_RE.match(str(raw).strip()):
        return str(raw).strip()
    return _new_block_id()


def _clip(text: Any, limit: int) -> str:
    return str(text or '').strip()[:limit]


def _sanitize_slide(slide: Any) -> dict[str, Any] | None:
    if not isinstance(slide, dict):
        return None
    title = _clip(slide.get('title'), 120)
    subtitle = _clip(slide.get('subtitle'), 200)
    image_url = _clip(slide.get('image_url'), 512)
    link_url = _clip(slide.get('link_url'), 512)
    if not title and not subtitle and not image_url:
        return None
    out: dict[str, Any] = {}
    if title:
        out['title'] = title
    if subtitle:
        out['subtitle'] = subtitle
    if image_url:
        out['image_url'] = image_url
    if link_url:
        out['link_url'] = link_url
    return out or None


def _sanitize_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    btype = _clip(block.get('type'), 32).lower()
    if btype not in _ALLOWED_TYPES:
        return None
    out: dict[str, Any] = {
        'id': _ensure_block_id(block.get('id')),
        'type': btype,
    }
    if btype == 'hero':
        variant = _clip(block.get('variant'), 16) or 'banner'
        if variant not in ('banner', 'compact'):
            variant = 'banner'
        out['variant'] = variant
    elif btype == 'search':
        out['placeholder'] = _clip(block.get('placeholder'), 64) or 'جستجو…'
    elif btype == 'slider':
        slides_in = block.get('slides')
        slides_out: list[dict[str, Any]] = []
        if isinstance(slides_in, list):
            for s in slides_in:
                ss = _sanitize_slide(s)
                if ss:
                    slides_out.append(ss)
        out['autoplay'] = bool(block.get('autoplay', True))
        out['slides'] = slides_out
    elif btype == 'categories':
        out['title'] = _clip(block.get('title'), 80) or 'دسته‌بندی‌ها'
        cols = int(block.get('columns') or 2)
        out['columns'] = 3 if cols >= 3 else 2
        limit = int(block.get('limit') or 8)
        out['limit'] = max(2, min(limit, 24))
    elif btype == 'featured':
        out['title'] = _clip(block.get('title'), 80) or 'محصولات ویژه'
        limit = int(block.get('limit') or 6)
        out['limit'] = max(1, min(limit, 24))
        layout = _clip(block.get('layout'), 16) or 'scroll'
        out['layout'] = 'grid' if layout == 'grid' else 'scroll'
    elif btype == 'products':
        out['title'] = _clip(block.get('title'), 80) or 'همه محصولات'
        layout = _clip(block.get('layout'), 16) or 'grid'
        out['layout'] = 'list' if layout == 'list' else 'grid'
        limit = int(block.get('limit') or 0)
        out['limit'] = max(0, min(limit, 48))
    elif btype == 'spacer':
        size = _clip(block.get('size'), 8) or 'md'
        out['size'] = size if size in ('sm', 'md', 'lg') else 'md'
    return out


def default_home_blocks() -> list[dict[str, Any]]:
    return [
        {'id': 'b_hero01', 'type': 'hero', 'variant': 'banner'},
        {'id': 'b_search01', 'type': 'search', 'placeholder': 'جستجو…'},
        {'id': 'b_cats01', 'type': 'categories', 'title': 'دسته‌بندی‌ها', 'columns': 2, 'limit': 8},
        {'id': 'b_feat01', 'type': 'featured', 'title': 'محصولات ویژه', 'limit': 6, 'layout': 'scroll'},
        {'id': 'b_prod01', 'type': 'products', 'title': 'همه محصولات', 'layout': 'grid', 'limit': 0},
    ]


def get_home_blocks(theme_config: Any) -> list[dict[str, Any]]:
    if not isinstance(theme_config, dict):
        return default_home_blocks()
    raw = theme_config.get('home_blocks')
    if not isinstance(raw, list) or not raw:
        return default_home_blocks()
    blocks: list[dict[str, Any]] = []
    for item in raw:
        b = _sanitize_block(item)
        if b:
            blocks.append(b)
    return blocks or default_home_blocks()


def sanitize_home_blocks(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, str):
        import json

        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return default_home_blocks()
    if not isinstance(data, list):
        return default_home_blocks()
    blocks: list[dict[str, Any]] = []
    for item in data:
        b = _sanitize_block(item)
        if b:
            blocks.append(b)
    return blocks or default_home_blocks()
