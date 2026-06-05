"""سرو فایل‌های SPA مینی‌اپ و callback پرداخت."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import CatalogOrder, CatalogSettings, Platform
from balebot.services import catalog_payment, zarinpal

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


@require_http_methods(['GET'])
def zarinpal_callback(request, public_id):
    catalog = get_object_or_404(CatalogSettings, public_id=public_id)
    order_id = request.GET.get('order_id')
    authority = (request.GET.get('Authority') or request.GET.get('authority') or '').strip()
    status = (request.GET.get('Status') or request.GET.get('status') or '').strip().upper()

    if not order_id or not authority:
        return HttpResponse(
            _payment_result_html('اطلاعات پرداخت ناقص است.', success=False, catalog=catalog),
            content_type='text/html; charset=utf-8',
        )

    order = get_object_or_404(
        CatalogOrder,
        pk=order_id,
        workspace=catalog.workspace,
        platform=catalog.platform,
    )

    if status != 'OK':
        order.status = CatalogOrder.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        return HttpResponse(
            _payment_result_html('پرداخت لغو شد یا ناموفق بود.', success=False, catalog=catalog),
            content_type='text/html; charset=utf-8',
        )

    try:
        catalog_payment.verify_zarinpal_order(order=order, catalog=catalog, authority=authority)
        return HttpResponse(
            _payment_result_html(
                f'پرداخت با موفقیت انجام شد. شماره سفارش: #{order.pk}',
                success=True,
                catalog=catalog,
            ),
            content_type='text/html; charset=utf-8',
        )
    except zarinpal.ZarinpalError as e:
        logger.warning('Zarinpal verify failed: %s', e)
        order.status = CatalogOrder.Status.FAILED
        order.save(update_fields=['status', 'updated_at'])
        return HttpResponse(
            _payment_result_html(str(e), success=False, catalog=catalog),
            content_type='text/html; charset=utf-8',
        )


def _payment_result_html(message: str, *, success: bool, catalog: CatalogSettings) -> str:
    color = '#16a34a' if success else '#dc2626'
    icon = '✅' if success else '❌'
    shop_url = f'/shop/{catalog.public_id}/'
    paid_q = '?paid=1' if success else ''
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>نتیجه پرداخت</title>
  <style>
    body {{ font-family: Tahoma, sans-serif; background:#f8fafc; margin:0; padding:2rem; }}
    .card {{ max-width:420px; margin:2rem auto; background:#fff; border-radius:16px; padding:2rem; text-align:center; box-shadow:0 4px 24px rgba(0,0,0,.08); }}
    .msg {{ color:{color}; font-size:1.1rem; margin:1rem 0 1.5rem; line-height:1.7; }}
    a {{ display:inline-block; background:#2563eb; color:#fff; text-decoration:none; padding:.75rem 1.5rem; border-radius:12px; }}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:3rem">{icon}</div>
    <div class="msg">{message}</div>
    <a href="{shop_url}{paid_q}">بازگشت به فروشگاه</a>
  </div>
</body>
</html>"""
