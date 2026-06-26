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
from balebot.services.workspace_subscription import workspace_block_reason

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


def _subscription_blocked_html() -> str:
    return (
        '<html lang="fa" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>فروشگاه غیرفعال</title>'
        '<style>body{font-family:Tahoma,sans-serif;display:flex;align-items:center;'
        'justify-content:center;min-height:100vh;margin:0;background:#f4f5f8;color:#16181d}'
        '.box{max-width:360px;padding:2rem;text-align:center;background:#fff;border-radius:16px;'
        'border:1px solid #e2e5ec;box-shadow:0 8px 32px rgba(22,24,29,.08)}'
        'h1{font-size:1.25rem;margin:0 0 .75rem}p{margin:0;color:#5c6370;line-height:1.7}</style>'
        '</head><body><div class="box">'
        '<h1>فروشگاه موقتاً غیرفعال است</h1>'
        '<p>اشتراک این فروشگاه منقضی شده. لطفاً با فروشنده تماس بگیرید.</p>'
        '</div></body></html>'
    )


def _check_catalog_subscription(public_id) -> str | None:
    if not public_id:
        return None
    try:
        UUID(str(public_id))
    except (TypeError, ValueError):
        return None
    try:
        catalog = CatalogSettings.objects.select_related('workspace').get(public_id=public_id)
    except CatalogSettings.DoesNotExist:
        return None
    return workspace_block_reason(catalog.workspace)


@xframe_options_exempt
@require_http_methods(['GET'])
def serve_miniapp(request, public_id=None, path=''):
    block_reason = _check_catalog_subscription(public_id)
    if block_reason:
        return _apply_miniapp_headers(HttpResponse(
            _subscription_blocked_html(),
            content_type='text/html; charset=utf-8',
            status=403,
        ))
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
