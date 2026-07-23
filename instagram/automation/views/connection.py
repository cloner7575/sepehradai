from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.http import JsonResponse

from instagram.mixins import InstagramPanelMixin
from instagram.automation.models import InstagramConnection
from instagram.automation.services.feature_flags import feature_enabled, meta_capability_status
from instagram.automation.services.oauth import (
    get_oauth_authorize_url,
    parse_oauth_state,
    exchange_code_for_token,
    exchange_long_lived_token,
    get_direct_instagram_profile,
    subscribe_connection_webhooks,
    DEFAULT_SCOPES,
    list_connectable_pages,
    connect_instagram_account,
    disconnect_connection,
    test_connection,
)
from instagram.automation.services.permissions import user_has_instagram_perm
from instagram.automation.services.meta_client import MetaAPIError
from instagram.automation.services.analytics import connection_health

logger = logging.getLogger(__name__)


class ConnectionListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/connection.html'

    def get(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_connection'):
            messages.error(request, 'اتصال اینستاگرام در پلن شما فعال نیست.')
            return redirect('instagram:dashboard')
        connections = InstagramConnection.objects.filter(workspace=ws)
        return render(
            request,
            self.template_name,
            {
                'connections': connections,
                'health': connection_health(ws),
                'messaging_status': meta_capability_status(ws, 'messaging'),
                'comments_status': meta_capability_status(ws, 'comments'),
                'private_reply_status': meta_capability_status(ws, 'private_reply'),
                'can_connect': user_has_instagram_perm(request.user, ws, 'instagram.connect'),
            },
        )


class OAuthStartView(InstagramPanelMixin, View):
    def get(self, request):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.connect'):
            messages.error(request, 'اجازهٔ اتصال ندارید.')
            return redirect('instagram:connection')
        if not feature_enabled(ws, 'instagram_connection'):
            messages.error(request, 'قابلیت اتصال فعال نیست.')
            return redirect('instagram:connection')
        try:
            url = get_oauth_authorize_url(workspace_id=ws.id, user_id=request.user.id)
        except ValueError:
            messages.error(request, 'تنظیمات محیطی Instagram OAuth کامل نیست.')
            return redirect('instagram:connection')
        return redirect(url)


class OAuthCallbackView(View):
    """Callback عمومی Meta — بدون InstagramPanelMixin چون از خارج می‌آید؛ state اعتبارسنجی می‌شود."""

    def get(self, request):
        error = request.GET.get('error')
        if error:
            messages.error(request, 'مجوز لازم از Meta در دسترس نیست. حساب را دوباره متصل کن یا تنظیمات مجوز را بررسی کن.')
            return redirect('instagram:connection')
        state = request.GET.get('state') or ''
        code = request.GET.get('code') or ''
        try:
            data = parse_oauth_state(state)
        except Exception:
            messages.error(request, 'نشست اتصال نامعتبر یا منقضی است.')
            return redirect('login')
        if not request.user.is_authenticated or request.user.id != data.get('user_id'):
            messages.error(request, 'برای تکمیل اتصال وارد شوید.')
            return redirect('login')
        from balebot.models import Workspace

        ws = get_object_or_404(Workspace, pk=data['workspace_id'])
        if not user_has_instagram_perm(request.user, ws, 'instagram.connect'):
            messages.error(request, 'اجازهٔ اتصال ندارید.')
            return redirect('instagram:connection')
        try:
            token_data = exchange_code_for_token(code)
            short = token_data['access_token']
            try:
                long_data = exchange_long_lived_token(short)
                user_token = long_data['access_token']
            except MetaAPIError:
                long_data = token_data
                user_token = short
            profile = get_direct_instagram_profile(
                user_token,
                fallback_user_id=str(token_data.get('user_id') or ''),
            )
            conn = connect_instagram_account(
                workspace=ws,
                user=request.user,
                page=profile,
                scopes=list(DEFAULT_SCOPES),
                auth_provider=InstagramConnection.AuthProvider.INSTAGRAM_LOGIN,
                token_data=long_data,
            )
            try:
                subscribe_connection_webhooks(conn)
            except MetaAPIError as exc:
                conn.webhook_status = InstagramConnection.WebhookStatus.ERROR
                conn.last_error_code = exc.internal_code
                conn.last_error_message_sanitized = exc.message_fa
                conn.save(update_fields=[
                    'webhook_status', 'last_error_code',
                    'last_error_message_sanitized', 'updated_at',
                ])
        except (MetaAPIError, Exception):
            logger.exception('OAuth callback failed')
            messages.error(request, 'اتصال به Meta ناموفق بود.')
            return redirect('instagram:connection')
        messages.success(request, 'اتصال امن اینستاگرام انجام شد.')
        return redirect('instagram:connection')


class ConnectionSelectView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/connection_select.html'

    def get(self, request):
        pages = request.session.get('ig_oauth_pages') or []
        return render(request, self.template_name, {'pages': pages})

    def post(self, request):
        ws = self.get_workspace()
        ig_id = request.POST.get('instagram_account_id') or ''
        pages = request.session.get('ig_oauth_pages') or []
        tokens = request.session.get('ig_oauth_page_tokens') or {}
        page_meta = next((p for p in pages if p.get('instagram_account_id') == ig_id), None)
        if not page_meta:
            messages.error(request, 'حساب انتخاب‌شده معتبر نیست.')
            return redirect('instagram:connection_select')
        page = dict(page_meta)
        page['page_access_token'] = tokens.get(ig_id) or ''
        try:
            connect_instagram_account(workspace=ws, user=request.user, page=page)
            messages.success(request, 'اتصال امن اینستاگرام انجام شد.')
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception:
            logger.exception('connect failed')
            messages.error(request, 'ذخیره اتصال ناموفق بود.')
        request.session.pop('ig_oauth_pages', None)
        request.session.pop('ig_oauth_page_tokens', None)
        request.session.pop('ig_oauth_workspace_id', None)
        return redirect('instagram:connection')


class ConnectionDisconnectView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.disconnect'):
            messages.error(request, 'اجازهٔ قطع اتصال ندارید.')
            return redirect('instagram:connection')
        conn = get_object_or_404(InstagramConnection, pk=pk, workspace=ws)
        disconnect_connection(conn, user=request.user)
        messages.success(request, 'اتصال قطع و توکن حذف شد.')
        return redirect('instagram:connection')


class ConnectionTestView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        conn = get_object_or_404(InstagramConnection, pk=pk, workspace=ws)
        try:
            result = test_connection(conn)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, **result})
            messages.success(request, f'اتصال سالم است — @{result.get("username")}')
        except MetaAPIError as exc:
            conn.last_error_code = exc.internal_code
            conn.last_error_message_sanitized = exc.message_fa
            conn.save(update_fields=['last_error_code', 'last_error_message_sanitized', 'updated_at'])
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': exc.message_fa, 'code': exc.internal_code})
            messages.error(request, exc.message_fa)
        return redirect('instagram:connection')


class ConnectionHealthApiView(InstagramPanelMixin, View):
    def get(self, request):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.logs.view'):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
        data = connection_health(ws)
        # serialize datetimes
        def ser(v):
            if hasattr(v, 'isoformat'):
                return v.isoformat()
            return v

        for c in data.get('connections') or []:
            for k in ('token_expires_at', 'last_webhook_at'):
                c[k] = ser(c.get(k))
        data['last_webhook_at'] = ser(data.get('last_webhook_at'))
        data['last_outbound_at'] = ser(data.get('last_outbound_at'))
        return JsonResponse({'ok': True, 'health': data})
