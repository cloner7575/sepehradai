"""دریافت وب‌هوک بله و تلگرام."""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import BotSettings, Platform
from balebot.services import webhook_logic

logger = logging.getLogger(__name__)


def _validate_platform(platform: str) -> str | None:
    if platform in (Platform.BALE, Platform.TELEGRAM):
        return platform
    return None


def _lookup_bot_settings(platform: str, secret: str) -> BotSettings | None:
    secret = (secret or '').strip()
    if not secret:
        return None
    return BotSettings.objects.filter(platform=platform, webhook_secret=secret).first()


def _process_webhook(cfg: BotSettings, body: bytes) -> JsonResponse:
    if not cfg.is_enabled:
        return JsonResponse({'ok': False}, status=403)

    try:
        payload = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning('Invalid webhook JSON (%s): %s', cfg.platform, e)
        return JsonResponse({'ok': True})

    try:
        if payload.get('message'):
            webhook_logic.handle_message(cfg, payload['message'])
        elif payload.get('callback_query'):
            webhook_logic.handle_callback(cfg, payload['callback_query'])
    except Exception:
        logger.exception('Webhook handler error (%s)', cfg.platform)
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def platform_webhook(request, platform: str, secret: str):
    normalized = _validate_platform(platform)
    if normalized is None:
        return JsonResponse({'ok': False}, status=404)
    cfg = _lookup_bot_settings(normalized, secret)
    if cfg is None:
        return JsonResponse({'ok': False}, status=404)
    return _process_webhook(cfg, request.body)


@csrf_exempt
@require_http_methods(['POST'])
def bale_webhook_legacy(request, secret: str):
    """مسیر قدیمی — فقط بله."""
    cfg = _lookup_bot_settings(Platform.BALE, secret)
    if cfg is None:
        return JsonResponse({'ok': False}, status=404)
    return _process_webhook(cfg, request.body)


def webhook_health(_request):
    return HttpResponse('ok')
