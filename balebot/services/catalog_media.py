"""ابزارهای رسانه کاتالوگ."""

from __future__ import annotations

import os

from urllib.parse import urlparse

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.ogv'}


def detect_media_type(filename: str) -> str:
    ext = os.path.splitext(filename or '')[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'file'


def _public_base_url(request, catalog=None) -> str:
    if catalog is not None:
        from balebot.models import BotSettings
        from balebot.services.public_url import resolve_public_base_url

        cfg = BotSettings.get_for_platform(catalog.workspace, catalog.platform)
        base = resolve_public_base_url(cfg).rstrip('/')
        if base:
            return base
    if request is None:
        return ''
    scheme = 'https' if request.is_secure() else 'http'
    forwarded = (request.META.get('HTTP_X_FORWARDED_PROTO') or '').split(',')[0].strip()
    if forwarded in ('http', 'https'):
        scheme = forwarded
    host = request.get_host()
    base = f'{scheme}://{host}'
    return _ensure_public_https(base)


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


def absolute_media_url(request, url: str, *, catalog=None) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return _ensure_public_https(url)
    path = url if url.startswith('/') else f'/{url}'
    base = _public_base_url(request, catalog)
    if base:
        return _ensure_public_https(f'{base}{path}')
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
        out.append(item)
    return out
