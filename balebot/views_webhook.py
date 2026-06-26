"""دریافت وب‌هوک بله و تلگرام."""

import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from balebot.models import BotSettings, Platform
from balebot.services import messenger_api
from balebot.services.workspace_subscription import workspace_can_operate
from balebot.tasks import dispatch_webhook_payload, process_webhook_update

logger = logging.getLogger(__name__)

_BOT_CFG_CACHE_TTL = 300


def _validate_platform(platform: str) -> str | None:
    if platform in (Platform.BALE, Platform.TELEGRAM):
        return platform
    return None


def _bot_settings_cache_key(platform: str, secret: str) -> str:
    return f'bot_cfg:{platform}:{secret}'


def _lookup_bot_settings(platform: str, secret: str) -> BotSettings | None:
    secret = (secret or '').strip()
    if not secret:
        return None

    cache_key = _bot_settings_cache_key(platform, secret)
    cached_pk = cache.get(cache_key)
    if cached_pk is not None:
        cfg = (
            BotSettings.objects.filter(pk=cached_pk, platform=platform, webhook_secret=secret)
            .select_related('workspace')
            .first()
        )
        if cfg is not None:
            return cfg
        cache.delete(cache_key)

    cfg = (
        BotSettings.objects.filter(platform=platform, webhook_secret=secret)
        .select_related('workspace')
        .first()
    )
    if cfg is not None:
        cache.set(cache_key, cfg.pk, _BOT_CFG_CACHE_TTL)
    return cfg


def _should_use_celery() -> bool:
    return bool(getattr(settings, 'WEBHOOK_USE_CELERY', False) and settings.CELERY_BROKER_URL)


def _enqueue_or_process(cfg: BotSettings, payload: dict) -> None:
    if _should_use_celery():
        try:
            process_webhook_update.delay(cfg.id, payload)
            return
        except Exception:
            logger.exception('Webhook Celery enqueue failed; falling back to sync')
    try:
        dispatch_webhook_payload(cfg, payload)
    except messenger_api.MessengerAPIError as exc:
        logger.warning('Webhook messenger API error (%s): %s', cfg.platform, exc)
    except Exception:
        logger.exception('Webhook handler error (%s)', cfg.platform)


def _process_webhook(cfg: BotSettings, body: bytes) -> JsonResponse:
    if not cfg.is_enabled:
        return JsonResponse({'ok': False}, status=403)

    if not workspace_can_operate(cfg.workspace):
        logger.warning(
            'Webhook ignored: workspace %s subscription inactive',
            cfg.workspace_id,
        )
        return JsonResponse({'ok': True})

    try:
        payload = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning('Invalid webhook JSON (%s): %s', cfg.platform, e)
        return JsonResponse({'ok': True})

    _enqueue_or_process(cfg, payload)
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
