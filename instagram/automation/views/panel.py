from __future__ import annotations

import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from instagram.mixins import InstagramPanelMixin
from instagram.automation.models import (
    InstagramAutomationRule,
    InstagramRuleCondition,
    InstagramFlow,
    InstagramFlowNode,
    InstagramFlowEdge,
    InstagramCommentAutomation,
    InstagramQuickReply,
    InstagramConnection,
    InstagramAuditLog,
    InstagramWebhookEvent,
)
from instagram.automation.services.feature_flags import feature_enabled, meta_capability_status
from instagram.automation.services.permissions import user_has_instagram_perm
from instagram.automation.services.flow_engine import (
    validate_flow,
    publish_flow,
    start_flow_execution,
    execute_flow_step,
)
from balebot.models import CatalogItem
from instagram.automation.services.analytics import analytics_summary, connection_health, sales_attribution
from instagram.automation.services.simple_replies import (
    PRESETS,
    apply_preset,
    shop_public_url,
    sync_rule_simple_flow,
)
from instagram.automation.tasks import retry_failed_instagram_event


class OverviewView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/overview.html'

    def get(self, request):
        ws = self.get_workspace()
        connections = InstagramConnection.objects.filter(
            workspace=ws,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        return render(
            request,
            self.template_name,
            {
                'summary': analytics_summary(ws),
                'health': connection_health(ws),
                'messaging_status': meta_capability_status(ws, 'messaging'),
                'has_connection': connections.exists(),
                'active_rules': InstagramAutomationRule.objects.filter(
                    workspace=ws, is_active=True
                ).count(),
                'shop_url': shop_public_url(ws),
                'presets': PRESETS,
            },
        )


class RuleListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/rules.html'

    def get(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_dm_automation'):
            messages.error(request, 'اتوماسیون دایرکت فعال نیست.')
            return redirect('instagram:overview')
        rules = InstagramAutomationRule.objects.filter(workspace=ws).select_related(
            'flow', 'connection'
        )
        return render(
            request,
            self.template_name,
            {'rules': rules, 'presets': PRESETS, 'shop_url': shop_public_url(ws)},
        )


class RulePresetApplyView(InstagramPanelMixin, View):
    def post(self, request, key: str):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.automation.create'):
            messages.error(request, 'اجازه ندارید.')
            return redirect('instagram:rules')
        conn = InstagramConnection.objects.filter(
            workspace=ws,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        ).first()
        try:
            rule = apply_preset(
                workspace=ws, user=request.user, preset_key=key, connection=conn
            )
            messages.success(
                request,
                f'سناریوی «{rule.name}» آماده شد. در صورت نیاز متن را ویرایش کنید.',
            )
            return redirect('instagram:rule_edit', pk=rule.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('instagram:rules')


class RuleEditView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/rule_edit.html'

    def get(self, request, pk=None):
        ws = self.get_workspace()
        rule = get_object_or_404(InstagramAutomationRule, pk=pk, workspace=ws) if pk else None
        connections = InstagramConnection.objects.filter(
            workspace=ws, connection_status='connected'
        )
        products = CatalogItem.objects.filter(workspace=ws, is_active=True).order_by('title')[:200]
        schedule = (rule.schedule if rule else {}) or {}
        return render(
            request,
            self.template_name,
            {
                'rule': rule,
                'connections': connections,
                'products': products,
                'shop_url': shop_public_url(ws),
                'keywords': ', '.join(schedule.get('keywords') or []),
                'reply_text': schedule.get('reply_text') or '',
                'exclude_keywords': ', '.join(schedule.get('exclude_keywords') or []),
                'match_operator': schedule.get('match_operator') or 'any_of',
                'content_scope': schedule.get('content_scope') or 'all',
                'selected_media_ids': ', '.join(schedule.get('selected_media_ids') or []),
                'trigger_type': rule.trigger_type if rule else 'keyword',
                'include_store_link': bool(schedule.get('include_store_link')),
                'handoff': bool(schedule.get('handoff')),
                'product_id': schedule.get('product_id') or '',
            },
        )

    def post(self, request, pk=None):
        ws = self.get_workspace()
        if not user_has_instagram_perm(
            request.user,
            ws,
            'instagram.automation.edit' if pk else 'instagram.automation.create',
        ):
            messages.error(request, 'اجازه ندارید.')
            return redirect('instagram:rules')
        rule = (
            get_object_or_404(InstagramAutomationRule, pk=pk, workspace=ws)
            if pk
            else InstagramAutomationRule(workspace=ws, created_by=request.user)
        )
        keywords = [k.strip() for k in (request.POST.get('keywords') or '').split(',') if k.strip()]
        exclude_keywords = [k.strip() for k in (request.POST.get('exclude_keywords') or '').split(',') if k.strip()]
        reply_text = (request.POST.get('reply_text') or '').strip()
        if not reply_text:
            messages.error(request, 'متن پاسخ را بنویسید.')
            return redirect(request.path)
        from instagram.automation.services.safe_templates import validate_template

        template_errors = validate_template(reply_text)
        if template_errors:
            messages.error(request, template_errors[0])
            return redirect(request.path)

        valid_triggers = {value for value, _ in InstagramAutomationRule.TriggerType.choices}
        trigger_type = request.POST.get('trigger_type') or InstagramAutomationRule.TriggerType.KEYWORD
        if trigger_type not in valid_triggers:
            messages.error(request, 'نوع ورودی قانون معتبر نیست.')
            return redirect(request.path)
        keyword_required = trigger_type in {
            InstagramAutomationRule.TriggerType.KEYWORD,
            InstagramAutomationRule.TriggerType.EXACT_TEXT,
            InstagramAutomationRule.TriggerType.STARTS_WITH,
            InstagramAutomationRule.TriggerType.ENDS_WITH,
            InstagramAutomationRule.TriggerType.ANY_KEYWORDS,
            InstagramAutomationRule.TriggerType.ALL_KEYWORDS,
        }
        if keyword_required and not keywords:
            messages.error(request, 'حداقل یک عبارت برای تطبیق لازم است.')
            return redirect(request.path)

        operator = request.POST.get('match_operator') or 'any_of'
        if operator not in {'eq', 'contains', 'starts_with', 'ends_with', 'any_of', 'all_of'}:
            operator = 'any_of'
        content_scope = request.POST.get('content_scope') or 'all'
        if content_scope not in {'all', 'selected', 'product_bound'}:
            content_scope = 'all'
        selected_media_ids = [
            value.strip() for value in (request.POST.get('selected_media_ids') or '').split(',') if value.strip()
        ]
        product_raw = request.POST.get('product_id') or ''
        product = CatalogItem.objects.filter(
            pk=int(product_raw) if product_raw.isdigit() else 0,
            workspace=ws,
            is_active=True,
        ).first()
        product_id = product.pk if product else None

        default_name = f'پاسخ به {keywords[0]}' if keywords else f'قانون {trigger_type}'
        rule.name = (request.POST.get('name') or default_name)[:200]
        rule.description = request.POST.get('description') or ''
        rule.trigger_type = trigger_type
        rule.match_mode = InstagramAutomationRule.MatchMode.ALL
        rule.priority = int(request.POST.get('priority') or 50)
        rule.cooldown_seconds = int(request.POST.get('cooldown_seconds') or 120)
        rule.stop_after_match = True
        rule.is_active = request.POST.get('is_active') == '1'
        conn_id = request.POST.get('connection_id') or ''
        rule.connection_id = int(conn_id) if conn_id else None
        rule.schedule = {
            'keywords': keywords, 'exclude_keywords': exclude_keywords,
            'match_operator': operator, 'content_scope': content_scope,
            'selected_media_ids': selected_media_ids, 'product_id': product_id,
        }
        rule.save()

        InstagramRuleCondition.objects.filter(rule=rule).delete()
        if keywords:
            InstagramRuleCondition.objects.create(
                rule=rule,
                field='text',
                operator=operator,
                value=keywords if operator in {'any_of', 'all_of'} else keywords[0], normalize_persian=True
            )
        for excluded in exclude_keywords:
            InstagramRuleCondition.objects.create(
                rule=rule, field='text', operator='not_contains', value=excluded, normalize_persian=True
            )
        sync_rule_simple_flow(
            rule=rule,
            reply_text=reply_text,
            include_store_link=request.POST.get('include_store_link') == '1',
            product_id=product_id,
            handoff=request.POST.get('handoff') == '1',
            user=request.user,
        )
        messages.success(request, 'پاسخ خودکار ذخیره شد.')
        return redirect('instagram:rules')


class RuleToggleView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        rule = get_object_or_404(InstagramAutomationRule, pk=pk, workspace=ws)
        rule.is_active = not rule.is_active
        rule.save(update_fields=['is_active', 'updated_at'])
        return redirect('instagram:rules')


class FlowListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/flows.html'

    def get(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_flow_builder'):
            messages.error(request, 'سناریوی چندمرحله‌ای فعال نیست.')
            return redirect('instagram:overview')
        flows = InstagramFlow.objects.filter(workspace=ws).exclude(
            description='ساخته‌شده خودکار از پاسخ ساده',
        )
        return render(request, self.template_name, {'flows': flows})


class FlowEditView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/flow_edit.html'

    def get(self, request, pk=None):
        ws = self.get_workspace()
        flow = get_object_or_404(InstagramFlow, pk=pk, workspace=ws) if pk else None
        definition = (flow.definition if flow else None) or {'nodes': [], 'edges': []}
        return render(
            request,
            self.template_name,
            {
                'flow': flow,
                'definition_json': json.dumps(definition, ensure_ascii=False),
            },
        )

    def post(self, request, pk=None):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.automation.edit'):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
        flow = get_object_or_404(InstagramFlow, pk=pk, workspace=ws) if pk else InstagramFlow(workspace=ws, created_by=request.user)
        flow.name = (request.POST.get('name') or request.POST.get('title') or 'فلو جدید')[:200]
        flow.description = request.POST.get('description') or ''
        raw = request.POST.get('definition') or '{}'
        try:
            definition = json.loads(raw)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'JSON نامعتبر'}, status=400)
        flow.definition = definition
        flow.entry_node_id = definition.get('entry') or flow.entry_node_id or ''
        if not flow.entry_node_id and definition.get('nodes'):
            flow.entry_node_id = definition['nodes'][0].get('id') or ''
        flow.save()
        # sync nodes/edges for relational engine
        InstagramFlowNode.objects.filter(flow=flow).delete()
        key_to_node = {}
        for n in definition.get('nodes') or []:
            node = InstagramFlowNode.objects.create(
                flow=flow,
                node_key=n.get('id') or n.get('key'),
                node_type=n.get('type') or 'send_text',
                position_x=float(n.get('x') or 0),
                position_y=float(n.get('y') or 0),
                config=n.get('config') or {},
            )
            key_to_node[node.node_key] = node
        for e in definition.get('edges') or []:
            src = key_to_node.get(e.get('source'))
            tgt = key_to_node.get(e.get('target'))
            if src and tgt:
                InstagramFlowEdge.objects.create(
                    flow=flow,
                    source_node=src,
                    target_node=tgt,
                    condition_key=e.get('condition') or '',
                    priority=int(e.get('priority') or 0),
                )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'id': flow.id})
        messages.success(request, 'فلو ذخیره شد.')
        return redirect('instagram:flow_edit', pk=flow.id)


class FlowPublishView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.automation.publish'):
            messages.error(request, 'اجازه انتشار ندارید.')
            return redirect('instagram:flows')
        flow = get_object_or_404(InstagramFlow, pk=pk, workspace=ws)
        try:
            publish_flow(flow)
            messages.success(request, 'فلو منتشر شد.')
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect('instagram:flow_edit', pk=pk)


class FlowTestView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        flow = get_object_or_404(InstagramFlow, pk=pk, workspace=ws)
        from instagram.automation.models import InstagramContact, InstagramConnection

        conn = InstagramConnection.objects.filter(workspace=ws).first()
        if not conn:
            return JsonResponse({'ok': False, 'error': 'اتصالی نیست'}, status=400)
        contact, _ = InstagramContact.objects.get_or_create(
            connection=conn,
            instagram_scoped_user_id='test-user',
            defaults={'workspace': ws, 'display_name': 'کاربر تست'},
        )
        execution = start_flow_execution(flow=flow, contact=contact, is_test_mode=True)
        for _ in range(20):
            execution = execute_flow_step(execution)
            if execution.status != execution.Status.RUNNING:
                break
        return JsonResponse({'ok': True, 'status': execution.status, 'log': execution.log})


class FlowDuplicateView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        flow = get_object_or_404(InstagramFlow, pk=pk, workspace=ws)
        clone = InstagramFlow.objects.create(
            workspace=ws,
            name=f'{flow.name} (کپی)',
            description=flow.description,
            version=1,
            status=InstagramFlow.Status.DRAFT,
            entry_node_id=flow.entry_node_id,
            definition=flow.definition,
            created_by=request.user,
            parent_flow=flow,
        )
        messages.success(request, 'فلو کپی شد.')
        return redirect('instagram:flow_edit', pk=clone.id)


class CommentAutomationListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/comments.html'

    def get(self, request):
        ws = self.get_workspace()
        status = meta_capability_status(ws, 'comments')
        items = InstagramCommentAutomation.objects.filter(workspace=ws)
        connections = InstagramConnection.objects.filter(
            workspace=ws,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        return render(
            request,
            self.template_name,
            {
                'items': items,
                'connections': connections,
                'capability_status': status,
                'private_reply_status': meta_capability_status(ws, 'private_reply'),
                'follow_check_unsupported': True,
            },
        )

    def post(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_comment_automation'):
            messages.error(request, 'اتوماسیون کامنت فعال نیست.')
            return redirect('instagram:comments')
        conn_id = request.POST.get('connection_id')
        conn = get_object_or_404(InstagramConnection, pk=conn_id, workspace=ws)
        auto = InstagramCommentAutomation.objects.create(
            workspace=ws,
            connection=conn,
            media_id=(request.POST.get('media_id') or '').strip(),
            include_keywords=[k.strip() for k in (request.POST.get('include_keywords') or '').split(',') if k.strip()],
            exclude_keywords=[k.strip() for k in (request.POST.get('exclude_keywords') or '').split(',') if k.strip()],
            public_replies=[request.POST.get('public_reply') or 'متشکریم! جزئیات در دایرکت ارسال شد.'],
            private_reply_text=request.POST.get('private_reply') or '',
            public_reply_enabled=True,
            private_reply_enabled=bool(request.POST.get('private_reply')),
            is_active=False,
            follow_check_mode=InstagramCommentAutomation.FollowCheckMode.DISABLED,
        )
        messages.success(request, 'اتوماسیون کامنت ایجاد شد (غیرفعال تا تأیید).')
        return redirect('instagram:comments')


class QuickReplyListView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/quick_replies.html'

    def get(self, request):
        ws = self.get_workspace()
        items = InstagramQuickReply.objects.filter(workspace=ws)
        return render(request, self.template_name, {'items': items})

    def post(self, request):
        ws = self.get_workspace()
        InstagramQuickReply.objects.create(
            workspace=ws,
            title=(request.POST.get('title') or '')[:120],
            text=request.POST.get('text') or '',
            shortcut=(request.POST.get('shortcut') or '')[:32],
            category=(request.POST.get('category') or '')[:64],
            created_by=request.user,
        )
        messages.success(request, 'پاسخ سریع ذخیره شد.')
        return redirect('instagram:quick_replies')


class AnalyticsView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/analytics.html'

    def get(self, request):
        ws = self.get_workspace()
        if not feature_enabled(ws, 'instagram_analytics'):
            messages.error(request, 'گزارش‌ها فعال نیست.')
            return redirect('instagram:overview')
        if not user_has_instagram_perm(request.user, ws, 'instagram.analytics.view'):
            messages.error(request, 'دسترسی ندارید.')
            return redirect('instagram:overview')
        return render(
            request,
            self.template_name,
            {
                'summary': analytics_summary(ws),
                'health': connection_health(ws),
                'sales_attribution': sales_attribution(ws),
            },
        )


class AnalyticsExportView(InstagramPanelMixin, View):
    def get(self, request):
        import csv
        from django.http import HttpResponse

        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.export'):
            return JsonResponse({'ok': False}, status=403)
        summary = analytics_summary(ws)
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="instagram-analytics.csv"'
        resp.write('\ufeff')
        w = csv.writer(resp)
        w.writerow(['metric', 'value'])
        for k, v in summary.items():
            w.writerow([k, v])
        return resp


class LogsView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/logs.html'

    def get(self, request):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.logs.view'):
            messages.error(request, 'دسترسی ندارید.')
            return redirect('instagram:overview')
        events = InstagramWebhookEvent.objects.filter(workspace=ws).order_by('-received_at')[:100]
        audits = InstagramAuditLog.objects.filter(workspace=ws).order_by('-created_at')[:100]
        return render(request, self.template_name, {'events': events, 'audits': audits})


class EventReplayView(InstagramPanelMixin, View):
    def post(self, request, pk):
        ws = self.get_workspace()
        if not user_has_instagram_perm(request.user, ws, 'instagram.events.replay'):
            return JsonResponse({'ok': False}, status=403)
        ev = get_object_or_404(InstagramWebhookEvent, pk=pk, workspace=ws)
        retry_failed_instagram_event.delay(ev.id)
        InstagramAuditLog.objects.create(
            workspace=ws,
            actor_type=InstagramAuditLog.ActorType.USER,
            actor_id=str(request.user.id),
            action='instagram.events.replay',
            entity_type='InstagramWebhookEvent',
            entity_id=str(ev.id),
        )
        messages.success(request, 'رویداد برای اجرای مجدد در صف قرار گرفت.')
        return redirect('instagram:logs')


class ContactsView(InstagramPanelMixin, View):
    template_name = 'instagram/automation/contacts.html'

    def get(self, request):
        from instagram.automation.models import InstagramContact

        ws = self.get_workspace()
        contacts = InstagramContact.objects.filter(workspace=ws).select_related('subscriber')[:200]
        return render(request, self.template_name, {'contacts': contacts})
