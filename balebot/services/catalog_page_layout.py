"""بلوک‌های صفحهٔ اصلی مینی‌اپ (سایت‌ساز گرافیکی)."""

from __future__ import annotations

import re
import uuid
from typing import Any

_BLOCK_ID_RE = re.compile(r'^b_[a-f0-9]{8}$')
_HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{3,8}$')
_TARGET_KINDS = frozenset({'category', 'item', 'tag', 'url', 'home', 'flash_sale'})
_CAROUSEL_SOURCES = frozenset({
    'featured', 'newest', 'bestselling', 'discounted', 'flash_sale', 'category', 'tag',
})
_RICH_TEXT_TAGS = frozenset({'p', 'b', 'i', 'ul', 'li', 'a', 'br', 'strong', 'em'})

_ALLOWED_TYPES = frozenset({
    'hero',
    'search',
    'slider',
    'categories',
    'featured',
    'products',
    'spacer',
    'announcement_bar',
    'story_bar',
    'countdown',
    'coupon',
    'product_carousel',
    'banner_grid',
    'video',
    'testimonials',
    'trust_badges',
    'faq',
    'info',
    'bundle',
    'rich_text',
})


def _new_block_id() -> str:
    return f'b_{uuid.uuid4().hex[:8]}'


def _ensure_block_id(raw: str | None) -> str:
    if raw and _BLOCK_ID_RE.match(str(raw).strip()):
        return str(raw).strip()
    return _new_block_id()


def _clip(text: Any, limit: int) -> str:
    return str(text or '').strip()[:limit]


def _sanitize_color(raw: Any, default: str = '') -> str:
    s = _clip(raw, 16)
    if s and _HEX_COLOR_RE.match(s):
        return s
    return default


def _sanitize_target(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    kind = _clip(raw.get('kind'), 16).lower()
    value = _clip(raw.get('value'), 256)
    if kind in ('home', 'flash_sale'):
        return {'kind': kind, 'value': ''}
    if kind not in _TARGET_KINDS or not value:
        return None
    return {'kind': kind, 'value': value}


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


def _sanitize_story_slide(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    image = _clip(raw.get('image'), 512)
    text = _clip(raw.get('text'), 500)
    target = _sanitize_target(raw.get('target'))
    duration = int(raw.get('duration') or 5)
    duration = max(2, min(duration, 30))
    if not image and not text:
        return None
    out: dict[str, Any] = {'duration': duration}
    if image:
        out['image'] = image
    if text:
        out['text'] = text
    if target:
        out['target'] = target
    return out


def _sanitize_story_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = _clip(raw.get('title'), 64)
    image = _clip(raw.get('image'), 512)
    target = _sanitize_target(raw.get('target'))
    slides_raw = raw.get('slides')
    slides: list[dict[str, Any]] = []
    if isinstance(slides_raw, list):
        for s in slides_raw:
            slide = _sanitize_story_slide(s)
            if slide:
                slides.append(slide)
    if not slides and (image or target):
        legacy: dict[str, Any] = {'duration': 5}
        if image:
            legacy['image'] = image
        if target:
            legacy['target'] = target
        slides = [legacy]
    if not title and not image and not slides:
        return None
    out: dict[str, Any] = {}
    if title:
        out['title'] = title
    if image:
        out['image'] = image
    if target and not slides:
        out['target'] = target
    if slides:
        out['slides'] = slides
    return out or None


def _sanitize_banner_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    image = _clip(raw.get('image'), 512)
    target = _sanitize_target(raw.get('target'))
    out: dict[str, Any] = {'image': image}
    if target:
        out['target'] = target
    return out


def _sanitize_faq_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    q = _clip(raw.get('q'), 200)
    a = _clip(raw.get('a'), 1000)
    if not q or not a:
        return None
    return {'q': q, 'a': a}


def _sanitize_testimonial(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = _clip(raw.get('name'), 64)
    text = _clip(raw.get('text'), 500)
    if not text:
        return None
    rating = int(raw.get('rating') or 5)
    rating = max(1, min(rating, 5))
    out: dict[str, Any] = {'text': text, 'rating': rating}
    if name:
        out['name'] = name
    image = _clip(raw.get('image'), 512)
    if image:
        out['image'] = image
    return out


def _sanitize_trust_badge(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    icon = _clip(raw.get('icon'), 8)
    label = _clip(raw.get('label'), 64)
    if not label:
        return None
    out: dict[str, Any] = {'label': label}
    if icon:
        out['icon'] = icon
    return out


def _sanitize_rich_html(raw: str) -> str:
    """Whitelist ساده برای HTML بلوک rich_text."""
    import html as html_mod

    text = str(raw or '')
    if not text.strip():
        return ''
    # حذف تگ‌های غیرمجاز با regex ساده
    def _repl_tag(m: re.Match) -> str:
        tag = m.group(1).lower()
        if tag in _RICH_TEXT_TAGS:
            return m.group(0)
        return ''

    cleaned = re.sub(r'</?([a-zA-Z][a-zA-Z0-9]*)[^>]*>', _repl_tag, text)
    cleaned = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', cleaned, flags=re.I)
    cleaned = re.sub(r'javascript:', '', cleaned, flags=re.I)
    return cleaned[:8000]


def _sanitize_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    btype = _clip(block.get('type'), 32).lower()
    if btype not in _ALLOWED_TYPES:
        return None
    if block.get('visible') is False:
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
    elif btype == 'announcement_bar':
        out['text'] = _clip(block.get('text'), 200) or 'اعلان فروشگاه'
        out['link'] = _clip(block.get('link'), 512)
        out['bg'] = _sanitize_color(block.get('bg'), '#111111')
        out['color'] = _sanitize_color(block.get('color'), '#ffffff')
        out['dismissible'] = bool(block.get('dismissible', True))
    elif btype == 'story_bar':
        items_out: list[dict[str, Any]] = []
        for raw in block.get('items') or []:
            si = _sanitize_story_item(raw)
            if si:
                items_out.append(si)
        if not items_out:
            items_out = [{'title': 'استوری', 'image': '', 'slides': [{'duration': 5}]}]
        out['items'] = items_out[:20]
    elif btype == 'countdown':
        out['title'] = _clip(block.get('title'), 120) or 'فروش ویژه'
        out['ends_at'] = _clip(block.get('ends_at'), 32)
        if not out['ends_at']:
            from datetime import timedelta

            from django.utils import timezone

            out['ends_at'] = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        out['cta_label'] = _clip(block.get('cta_label'), 40) or 'مشاهده حراج'
        cta = _sanitize_target(block.get('cta_target'))
        if cta:
            out['cta_target'] = cta
        else:
            out['cta_target'] = {'kind': 'flash_sale', 'value': ''}
        out['accent'] = _sanitize_color(block.get('accent'), '#c2402f')
    elif btype == 'coupon':
        out['title'] = _clip(block.get('title'), 120)
        out['code'] = _clip(block.get('code'), 40) or 'SALE'
        out['subtitle'] = _clip(block.get('subtitle'), 120)
        out['copy_label'] = _clip(block.get('copy_label'), 32) or 'کپی کد'
    elif btype == 'product_carousel':
        source = _clip(block.get('source'), 16).lower() or 'featured'
        if source not in _CAROUSEL_SOURCES:
            source = 'featured'
        out['title'] = _clip(block.get('title'), 80) or 'محصولات'
        out['source'] = source
        out['category'] = _clip(block.get('category'), 120)
        out['tag'] = _clip(block.get('tag'), 120)
        limit = int(block.get('limit') or 10)
        out['limit'] = max(1, min(limit, 24))
    elif btype == 'banner_grid':
        cols = int(block.get('columns') or 2)
        out['columns'] = max(2, min(cols, 4))
        items_out = []
        for raw in block.get('items') or []:
            bi = _sanitize_banner_item(raw)
            if bi:
                items_out.append(bi)
        if not items_out:
            items_out = [{'image': '', 'target': {'kind': 'category', 'value': ''}}]
        out['items'] = items_out[:8]
    elif btype == 'video':
        out['title'] = _clip(block.get('title'), 120)
        out['source'] = 'url'
        out['url'] = _clip(block.get('url'), 512)
        out['poster'] = _clip(block.get('poster'), 512)
    elif btype == 'testimonials':
        out['title'] = _clip(block.get('title'), 80) or 'نظر مشتری‌ها'
        items_out = []
        for raw in block.get('items') or []:
            t = _sanitize_testimonial(raw)
            if t:
                items_out.append(t)
        if not items_out:
            items_out = [{'name': 'مشتری', 'text': 'نظر نمونه', 'rating': 5}]
        out['items'] = items_out[:20]
    elif btype == 'trust_badges':
        items_out = []
        for raw in block.get('items') or []:
            b = _sanitize_trust_badge(raw)
            if b:
                items_out.append(b)
        if not items_out:
            items_out = [
                {'icon': '✅', 'label': 'اصالت کالا'},
                {'icon': '🚚', 'label': 'ارسال سریع'},
            ]
        out['items'] = items_out[:12]
    elif btype == 'faq':
        out['title'] = _clip(block.get('title'), 80) or 'سوالات متداول'
        items_out = []
        for raw in block.get('items') or []:
            f = _sanitize_faq_item(raw)
            if f:
                items_out.append(f)
        if not items_out:
            items_out = [{'q': 'سوال نمونه؟', 'a': 'پاسخ نمونه'}]
        out['items'] = items_out[:30]
    elif btype == 'info':
        out['about'] = _clip(block.get('about'), 2000)
        phones_in = block.get('phones')
        phones: list[str] = []
        if isinstance(phones_in, list):
            for p in phones_in:
                ph = _clip(p, 20)
                if ph:
                    phones.append(ph)
        out['phones'] = phones[:5]
        out['address'] = _clip(block.get('address'), 300)
        out['hours'] = _clip(block.get('hours'), 120)
        loc = block.get('location')
        if isinstance(loc, dict):
            try:
                lat = float(loc.get('lat'))
                lng = float(loc.get('lng'))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    out['location'] = {'lat': lat, 'lng': lng}
            except (TypeError, ValueError):
                pass
        socials_in = block.get('socials')
        if isinstance(socials_in, dict):
            socials: dict[str, str] = {}
            for key in ('instagram', 'eitaa', 'telegram', 'website'):
                val = _clip(socials_in.get(key), 512)
                if val:
                    socials[key] = val
            if socials:
                out['socials'] = socials
        if not any([out.get('about'), out.get('phones'), out.get('address'), out.get('hours')]):
            out['about'] = 'اطلاعات تماس فروشگاه'
    elif btype == 'bundle':
        out['title'] = _clip(block.get('title'), 120)
        slugs_in = block.get('item_slugs')
        slugs: list[str] = []
        if isinstance(slugs_in, list):
            for s in slugs_in:
                slug = _clip(s, 120)
                if slug:
                    slugs.append(slug)
        out['item_slugs'] = slugs[:10]
        try:
            out['bundle_price'] = max(0, int(block.get('bundle_price') or 0))
        except (TypeError, ValueError):
            out['bundle_price'] = 0
        out['badge'] = _clip(block.get('badge'), 64)
    elif btype == 'rich_text':
        html = _sanitize_rich_html(block.get('html')) or '<p>متن دلخواه</p>'
        out['title'] = _clip(block.get('title'), 120)
        out['html'] = html
        align = _clip(block.get('align'), 8) or 'right'
        out['align'] = align if align in ('right', 'center', 'left') else 'right'
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
