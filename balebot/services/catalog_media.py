"""ابزارهای رسانه کاتالوگ."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.ogv'}
_ALLOWED_MEDIA_PREFIXES = ('catalog/', 'flow_media/', 'campaigns/', 'inbound/')


def detect_media_type(filename: str) -> str:
    ext = os.path.splitext(filename or '')[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'file'


def _ensure_public_https(url: str) -> str:
    """WebView بله/تلگرام روی HTTPS فقط تصاویر HTTPS را لود می‌کند."""
    if not url:
        return ''
    if url.startswith('https://'):
        return url
    if url.startswith('http://'):
        host = urlparse(url).hostname or ''
        if host.lower() in {'localhost', '127.0.0.1', '0.0.0.0', '::1'}:
            return url
        return 'https://' + url[7:]
    return url


def request_public_base_url(request) -> str:
    """دامنهٔ واقعی درخواست — همان چیزی که کاربر مینی‌اپ را با آن باز کرده."""
    if not request:
        return ''
    forwarded = (request.META.get('HTTP_X_FORWARDED_PROTO') or '').split(',')[0].strip()
    if forwarded in ('http', 'https'):
        scheme = forwarded
    else:
        scheme = 'https' if request.is_secure() else 'http'
    return _ensure_public_https(f'{scheme}://{request.get_host()}').rstrip('/')


def media_relative_path(url: str) -> str:
    raw = (url or '').strip().lstrip('/')
    media_prefix = (settings.MEDIA_URL or '/media/').strip('/')
    if media_prefix and raw.startswith(f'{media_prefix}/'):
        return raw[len(media_prefix) + 1 :]
    return raw


def safe_media_relative_path(raw: str) -> str | None:
    rel = media_relative_path(raw)
    if not rel or '..' in rel or rel.startswith('/'):
        return None
    if not any(rel.startswith(prefix) for prefix in _ALLOWED_MEDIA_PREFIXES):
        return None
    return rel


def resolve_media_file(relative_path: str) -> Path | None:
    safe = safe_media_relative_path(relative_path)
    if not safe:
        return None
    root = Path(settings.MEDIA_ROOT).resolve()
    full = (root / safe).resolve()
    if not str(full).startswith(str(root)):
        return None
    if not full.is_file():
        return None
    return full


def guess_content_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(str(path))
    return content_type or 'application/octet-stream'


def absolute_media_url(request, url: str, *, catalog=None) -> str:
    """آدرس مطلق HTTPS برای مینی‌اپ — از همان دامنهٔ درخواست و API اختصاصی."""
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return _ensure_public_https(url)

    rel = media_relative_path(url)
    if catalog and request and rel:
        base = request_public_base_url(request)
        if base:
            return f'{base}/api/shop/{catalog.public_id}/media/{rel}'

    path = url if url.startswith('/') else f'/{url}'
    if request:
        return _ensure_public_https(request.build_absolute_uri(path))
    return path


def absolutize_home_blocks(
    blocks: list[dict],
    request,
    *,
    catalog=None,
) -> list[dict]:
    """تبدیل URLهای نسبی بلوک‌های صفحهٔ اصلی به آدرس مطلق HTTPS."""
    out: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        item = dict(block)
        if item.get('type') == 'slider':
            slides_out = []
            for slide in item.get('slides') or []:
                if not isinstance(slide, dict):
                    continue
                s = dict(slide)
                if s.get('image_url'):
                    s['image_url'] = absolute_media_url(request, s['image_url'], catalog=catalog)
                slides_out.append(s)
            item['slides'] = slides_out
        elif item.get('type') == 'story_bar':
            items_out = []
            for story in item.get('items') or []:
                if not isinstance(story, dict):
                    continue
                s = dict(story)
                if s.get('image'):
                    s['image'] = absolute_media_url(request, s['image'], catalog=catalog)
                items_out.append(s)
            item['items'] = items_out
        elif item.get('type') == 'banner_grid':
            items_out = []
            for banner in item.get('items') or []:
                if not isinstance(banner, dict):
                    continue
                b = dict(banner)
                if b.get('image'):
                    b['image'] = absolute_media_url(request, b['image'], catalog=catalog)
                items_out.append(b)
            item['items'] = items_out
        elif item.get('type') == 'video':
            if item.get('poster'):
                item['poster'] = absolute_media_url(request, item['poster'], catalog=catalog)
        elif item.get('type') == 'testimonials':
            items_out = []
            for t in item.get('items') or []:
                if not isinstance(t, dict):
                    continue
                ti = dict(t)
                if ti.get('image'):
                    ti['image'] = absolute_media_url(request, ti['image'], catalog=catalog)
                items_out.append(ti)
            item['items'] = items_out
        out.append(item)
    return out
