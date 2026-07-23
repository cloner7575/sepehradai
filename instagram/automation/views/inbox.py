from __future__ import annotations

import logging

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from instagram.mixins import InstagramPanelMixin
from instagram.automation.models import (
    InstagramConversation,
    InstagramMessage,
    InstagramContact,
    InstagramAuditLog,
)
from instagram.automation.services.feature_flags import feature_enabled
from instagram.automation.services.permissions import user_has_instagram_perm
from instagram.automation.services.oauth import client_for_connection
from instagram.automation.services.meta_client import MetaAPIError

logger = logging.getLogger(__name__)


class InboxListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/inbox.html'

    def get(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_inbox'):
            messages.error(request, 'صندوق پیام اینستاگرام فعال نیست.')
            return redirect('instagram:dashboard')
        if not user_has_instagram_perm(request.user, ws, 'instagram.inbox.view'):
            messages.error(request, 'دسترسی ندارید.')
            return redirect('instagram:dashboard')

        qs = (
            InstagramConversation.objects.filter(workspace=ws)
            .select_related('contact', 'connection', 'assigned_user')
            .order_by('-last_message_at', '-id')
        )
        q = (request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(contact__username__icontains=q)
                | Q(contact__display_name__icontains=q)
                | Q(contact__instagram_scoped_user_id__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        mode = request.GET.get('mode')
        if mode:
            qs = qs.filter(mode=mode)
        if request.GET.get('unread') == '1':
            qs = qs.filter(unread_count__gt=0)
        assigned = request.GET.get('assigned')
        if assigned == 'me':
            qs = qs.filter(assigned_user=request.user)
        elif assigned == 'none':
            qs = qs.filter(assigned_user__isnull=True)

        return render(
            request,
            self.template_name,
            {
                'conversations': qs[:100],
                'filters': {
                    'q': q,
                    'status': status or '',
                    'mode': mode or '',
                    'unread': request.GET.get('unread') or '',
                    'assigned': assigned or '',
                },
            },
        )


class InboxDetailView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/inbox_detail.html'

    def get(self, request, pk):
        ws = self.get_workspace()
        conv = get_object_or_404(
            InstagramConversation.objects.select_related('contact', 'connection'),
            pk=pk,
            workspace=ws,
        )
        messages_qs = conv.messages.filter(is_internal_note=False).order_by('created_at')
        notes = conv.messages.filter(is_internal_note=True).order_by('-created_at')[:20]
        if conv.unread_count:
            conv.unread_count = 0
            conv.save(update_fields=['unread_count', 'updated_at'])
        return render(
            request,
            self.template_name,
            {
                'conversation': conv,
                'chat_messages': messages_qs[:500],
                'notes': notes,
                'contact': conv.contact,
                'executions': conv.flow_executions.order_by('-started_at')[:10],
            },
        )


class InboxReplyView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.inbox.reply'):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
        conv = get_object_or_404(InstagramConversation, pk=pk, workspace=ws)
        text = (request.POST.get('text') or '').strip()
        if not text:
            messages.error(request, 'متن پیام خالی است.')
            return redirect('instagram:inbox_detail', pk=pk)
        from instagram.automation.services.messaging_window import is_messaging_window_open

        if not is_messaging_window_open(conv):
            messages.error(request, 'پنجره مجاز پاسخ Meta بسته شده است؛ منتظر پیام جدید مخاطب بمانید.')
            return redirect('instagram:inbox_detail', pk=pk)


        # Human takeover
        conv.mode = InstagramConversation.Mode.HUMAN
        if request.POST.get('pause_automation', '1') == '1':
            conv.automation_paused_permanent = True
        conv.assigned_user = request.user
        conv.save()

        InstagramAuditLog.objects.create(
            workspace=ws,
            actor_type=InstagramAuditLog.ActorType.USER,
            actor_id=str(request.user.id),
            action='instagram.inbox.reply',
            entity_type='InstagramConversation',
            entity_id=str(conv.id),
        )

        try:
            client = client_for_connection(conv.connection)
            result = client.send_text_message(
                ig_user_id=conv.connection.instagram_account_id,
                recipient_id=conv.contact.instagram_scoped_user_id,
                text=text,
            )
            InstagramMessage.objects.create(
                workspace=ws,
                conversation=conv,
                external_message_id=str(result.get('message_id') or ''),
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.AGENT,
                message_type='text',
                text=text,
                delivery_status=InstagramMessage.DeliveryStatus.SENT,
                sent_at=timezone.now(),
                created_by=request.user,
            )
            conv.last_message_at = timezone.now()
            conv.save(update_fields=['last_message_at', 'updated_at'])
            messages.success(request, 'پیام ارسال شد. پاسخ خودکار این گفت‌وگو موقتاً متوقف شد.')
        except MetaAPIError as exc:
            InstagramMessage.objects.create(
                workspace=ws,
                conversation=conv,
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.AGENT,
                message_type='text',
                text=text,
                delivery_status=InstagramMessage.DeliveryStatus.FAILED,
                failure_code=exc.internal_code,
                failure_message_sanitized=exc.message_fa,
                created_by=request.user,
            )
            messages.error(request, f'{exc.message_fa} ({exc.internal_code})')
        return redirect('instagram:inbox_detail', pk=pk)


class InboxAssignView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.inbox.assign'):
            messages.error(request, 'اجازه ندارید.')
            return redirect('instagram:inbox_detail', pk=pk)
        conv = get_object_or_404(InstagramConversation, pk=pk, workspace=ws)
        action = request.POST.get('action')
        if action == 'me':
            conv.assigned_user = request.user
        elif action == 'clear':
            conv.assigned_user = None
        conv.save(update_fields=['assigned_user', 'updated_at'])
        InstagramAuditLog.objects.create(
            workspace=ws,
            actor_type=InstagramAuditLog.ActorType.USER,
            actor_id=str(request.user.id),
            action='instagram.inbox.assign',
            entity_type='InstagramConversation',
            entity_id=str(conv.id),
            after_data_redacted={'assigned_user_id': conv.assigned_user_id},
        )
        return redirect('instagram:inbox_detail', pk=pk)


class InboxAutomationToggleView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        conv = get_object_or_404(InstagramConversation, pk=pk, workspace=ws)
        action = request.POST.get('action')
        if action == 'pause':
            conv.automation_paused_permanent = True
            conv.mode = InstagramConversation.Mode.HUMAN
            messages.info(request, 'پاسخ خودکار این گفت‌وگو موقتاً متوقف شد.')
        elif action == 'resume':
            conv.automation_paused_permanent = False
            conv.automation_paused_until = None
            conv.mode = InstagramConversation.Mode.AUTOMATION
            messages.success(request, 'اتوماسیون از سر گرفته شد.')
        elif action == 'spam':
            conv.status = InstagramConversation.Status.SPAM
            contact = conv.contact
            contact.is_blocked = True
            contact.save(update_fields=['is_blocked', 'updated_at'])
        elif action == 'close':
            conv.status = InstagramConversation.Status.CLOSED
            conv.close_reason = (request.POST.get('reason') or '')[:255]
        conv.save()
        return redirect('instagram:inbox_detail', pk=pk)


class InboxNoteView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        conv = get_object_or_404(InstagramConversation, pk=pk, workspace=ws)
        text = (request.POST.get('text') or '').strip()
        if text:
            InstagramMessage.objects.create(
                workspace=ws,
                conversation=conv,
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.SYSTEM,
                message_type='note',
                text=text,
                is_internal_note=True,
                delivery_status=InstagramMessage.DeliveryStatus.SENT,
                created_by=request.user,
                sent_at=timezone.now(),
            )
        return redirect('instagram:inbox_detail', pk=pk)


class InboxPollView(InstagramPanelMixin, View):
    def get(self, request, pk):
        ws = self.get_workspace()
        conv = get_object_or_404(InstagramConversation, pk=pk, workspace=ws)
        after = request.GET.get('after')
        qs = conv.messages.filter(is_internal_note=False).order_by('id')
        if after:
            qs = qs.filter(id__gt=int(after))
        data = [
            {
                'id': m.id,
                'direction': m.direction,
                'sender_type': m.sender_type,
                'text': m.text,
                'created_at': m.created_at.isoformat(),
            }
            for m in qs[:50]
        ]
        return JsonResponse({'ok': True, 'messages': data})


class ContactLinkSubscriberView(InstagramPanelMixin, View):
    def post(self, request, pk):
        from balebot.models import Subscriber
        from instagram.automation.services.contact_resolve import link_subscriber_manual

        ws = self.get_workspace()
        contact = get_object_or_404(InstagramContact, pk=pk, workspace=ws)
        sub_id = request.POST.get('subscriber_id')
        sub = get_object_or_404(Subscriber, pk=sub_id, workspace=ws)
        link_subscriber_manual(contact=contact, subscriber=sub)
        messages.success(request, 'مخاطب به CRM متصل شد.')
        conv = contact.conversations.order_by('-id').first()
        if conv:
            return redirect('instagram:inbox_detail', pk=conv.id)
        return redirect('instagram:inbox')
