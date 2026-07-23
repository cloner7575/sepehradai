from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from instagram.automation.services.oauth import verify_webhook_signature
from instagram.automation.services.webhook import ingest_webhook_payload
from instagram.automation.tasks import process_instagram_webhook

logger = logging.getLogger(__name__)


def _should_use_celery() -> bool:
    return bool(
        getattr(settings, 'WEBHOOK_USE_CELERY', False)
        and getattr(settings, 'CELERY_BROKER_URL', '')
    )


def _enqueue_or_process_event(event_id: int) -> None:
    if _should_use_celery():
        try:
            process_instagram_webhook.delay(event_id)
            return
        except Exception:
            logger.exception('Failed to enqueue IG event %s; falling back to sync', event_id)
    from instagram.automation.services.event_processor import process_webhook_event

    try:
        process_webhook_event(event_id)
    except Exception:
        logger.exception('Sync process failed for %s', event_id)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def meta_webhook(request):
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge', '')
        expected = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', '') or ''
        if mode == 'subscribe' and token and expected and token == expected:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('forbidden', status=403)

    raw = request.body
    sig = request.headers.get('X-Hub-Signature-256') or request.META.get(
        'HTTP_X_HUB_SIGNATURE_256', ''
    )
    if getattr(settings, 'META_APP_SECRET', '') and not verify_webhook_signature(raw, sig):
        logger.warning('IG webhook signature invalid')
        return JsonResponse({'ok': False}, status=403)

    try:
        payload = json.loads(raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': True})

    events = ingest_webhook_payload(payload)
    for ev in events:
        _enqueue_or_process_event(ev.id)

    return JsonResponse({'ok': True})
