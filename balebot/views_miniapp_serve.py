"""سرو فایل‌های SPA مینی‌اپ."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import CatalogSettings, Platform

logger = logging.getLogger(__name__)

BALE_SDK_URL = 'https://tapi.bale.ai/miniapp.js?3'
TELEGRAM_SDK_URL = 'https://telegram.org/js/telegram-web-app.js'
_MINIAPP_SDK_RE = re.compile(
    r'<script src="https://(?:tapi\.bale\.ai/miniapp\.js\?3|telegram\.org/js/telegram-web-app\.js)"'
    r' data-miniapp-sdk></script>',
)
_MINIAPP_SDK_BLOCK_RE = re.compile(
    r'<!-- MINIAPP_SDK -->.*?</script>',
    re.DOTALL,
)

MINIAPP_FRAME_CSP = (
    "frame-ancestors 'self' https://*.bale.ai https://web.bale.ai https://*.telegram.org;"
)


def _apply_miniapp_headers(response: HttpResponse | FileResponse) -> HttpResponse | FileResponse:
    response['Content-Security-Policy'] = MINIAPP_FRAME_CSP
    if 'X-Frame-Options' in response:
        del response['X-Frame-Options']
    return response

MINIAPP_INDEX_CANDIDATES = [
    Path(settings.BASE_DIR) / 'static' / 'miniapp' / 'index.html',
    Path(settings.BASE_DIR) / 'miniapp' / 'dist' / 'index.html',
]


def _find_index() -> Path | None:
    for p in MINIAPP_INDEX_CANDIDATES:
        if p.is_file():
            return p
    return None


def _catalog_platform(public_id) -> str:
    if not public_id:
        return Platform.BALE
    try:
        UUID(str(public_id))
    except (TypeError, ValueError):
        return Platform.BALE
    try:
        return CatalogSettings.objects.only('platform').get(public_id=public_id).platform
    except CatalogSettings.DoesNotExist:
        return Platform.BALE


def _inject_platform_sdk(html: str, platform: str) -> str:
    platform = Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE
    sdk_url = TELEGRAM_SDK_URL if platform == Platform.TELEGRAM else BALE_SDK_URL
    html = re.sub(
        r'<meta name="miniapp-platform" content="[^"]*"\s*/?>',
        f'<meta name="miniapp-platform" content="{platform}" />',
        html,
        count=1,
    )
    sdk_tag = f'<script src="{sdk_url}" data-miniapp-sdk></script>'
    if _MINIAPP_SDK_BLOCK_RE.search(html):
        html = _MINIAPP_SDK_BLOCK_RE.sub(sdk_tag, html, count=1)
    elif _MINIAPP_SDK_RE.search(html):
        html = _MINIAPP_SDK_RE.sub(sdk_tag, html, count=1)
    return html


@xframe_options_exempt
@require_http_methods(['GET'])
def serve_miniapp(request, public_id=None, path=''):
    index = _find_index()
    if not index:
        return _apply_miniapp_headers(HttpResponse(
            '<html dir="rtl"><body style="font-family:sans-serif;padding:2rem">'
            '<h1>مینی‌اپ در حال آماده‌سازی است</h1>'
            '<p>ابتدا <code>npm run build</code> را در پوشه miniapp اجرا کنید.</p>'
            '</body></html>',
            content_type='text/html; charset=utf-8',
        ))
    if path:
        static_root = index.parent
        asset = (static_root / path).resolve()
        if not str(asset).startswith(str(static_root.resolve())):
            raise Http404
        if asset.is_file():
            return _apply_miniapp_headers(FileResponse(asset.open('rb')))
    content = index.read_text(encoding='utf-8')
    content = _inject_platform_sdk(content, _catalog_platform(public_id))
    return _apply_miniapp_headers(HttpResponse(
        content,
        content_type='text/html; charset=utf-8',
    ))
