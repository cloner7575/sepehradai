from django.http import JsonResponse
from django.views import View

from instagram.mixins import InstagramPanelMixin
from instagram.automation.models import InstagramConversation
from instagram.automation.services.ai_assistant import suggest_reply, classify_intent
from django.shortcuts import get_object_or_404


class AISuggestReplyView(InstagramPanelMixin, View):
    def post(self, request, pk):
        return JsonResponse({'ok': False, 'error': 'feature_disabled'}, status=410)


class AIClassifyView(InstagramPanelMixin, View):
    def post(self, request, pk):
        return JsonResponse({'ok': False, 'error': 'feature_disabled'}, status=410)
