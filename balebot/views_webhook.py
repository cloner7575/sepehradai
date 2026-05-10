"""دریافت وب‌هوک بله."""

import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from balebot.services import webhook_logic

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['POST'])
def bale_webhook(request, secret: str):
    if secret != settings.BALE_WEBHOOK_SECRET:
        return JsonResponse({'ok': False}, status=403)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning('Invalid webhook JSON: %s', e)
        return JsonResponse({'ok': True})

    try:
        if body.get('message'):
            webhook_logic.handle_message(body['message'])
        elif body.get('callback_query'):
            webhook_logic.handle_callback(body['callback_query'])
    except Exception:
        logger.exception('Webhook handler error')
    return JsonResponse({'ok': True})


def webhook_health(_request):
    return HttpResponse('ok')
