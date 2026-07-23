from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from instagram.automation.models import InstagramContact


def _decode_signed_request(value: str) -> dict | None:
    try:
        signature, payload = value.split('.', 1)
        padded_sig = signature + '=' * (-len(signature) % 4)
        padded_payload = payload + '=' * (-len(payload) % 4)
        supplied = base64.urlsafe_b64decode(padded_sig)
        expected = hmac.new(
            settings.INSTAGRAM_APP_SECRET.encode('utf-8'),
            payload.encode('ascii'),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(supplied, expected):
            return None
        return json.loads(base64.urlsafe_b64decode(padded_payload).decode('utf-8'))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None


class PrivacyPolicyView(View):
    def get(self, request):
        return render(request, 'instagram/automation/privacy_policy.html')


class DataDeletionView(View):
    def get(self, request):
        return render(request, 'instagram/automation/data_deletion.html')

    def post(self, request):
        payload = _decode_signed_request(request.POST.get('signed_request') or '')
        user_id = str((payload or {}).get('user_id') or '')
        if not user_id:
            return JsonResponse({'error': 'invalid_signed_request'}, status=400)
        contacts = InstagramContact.objects.filter(instagram_scoped_user_id=user_id)
        workspace_ids = list(contacts.values_list('workspace_id', flat=True).distinct())
        contacts.delete()
        confirmation = secrets.token_urlsafe(16)
        return JsonResponse({
            'url': request.build_absolute_uri(f'?confirmation={confirmation}'),
            'confirmation_code': confirmation,
            'workspaces_affected': len(workspace_ids),
        })
