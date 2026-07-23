from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from instagram.automation.models import (
    InstagramFlow,
    InstagramFlowExecution,
    InstagramFlowNode,
    InstagramMessage,
)
from instagram.automation.services.oauth import client_for_connection
from instagram.automation.services.meta_client import MetaAPIError

logger = logging.getLogger(__name__)


SUPPORTED_NODE_TYPES = {
    'send_text',
    'send_product',
    'add_tag',
    'condition',
    'assign_agent',
    'pause_automation',
    'stop',
}

_PUBLIC_PATH_RE = re.compile(r'(?<![A-Za-z0-9_:/])(/(?:shop|instagram/r)/[^\s<]*)')


def _absolute_public_urls(text: str) -> str:
    base_url = str(getattr(settings, 'BASE_URL', '') or '').strip().rstrip('/')
    if not base_url or not text:
        return text
    return _PUBLIC_PATH_RE.sub(lambda match: f'{base_url}{match.group(1)}', text)


def validate_flow(flow: InstagramFlow) -> list[str]:
    errors: list[str] = []
    nodes = list(flow.nodes.all())
    if not nodes:
        # fallback to definition JSON
        definition = flow.definition or {}
        nodes_data = definition.get('nodes') or []
        if not nodes_data:
            errors.append('فلو هیچ نودی ندارد.')
            return errors
        keys = {n.get('id') or n.get('key') for n in nodes_data}
        if None in keys or len(keys) != len(nodes_data):
            errors.append('شناسه نودها باید یکتا و غیرخالی باشد.')
        edges = definition.get('edges') or []
        targets = {e.get('target') for e in edges}
        sources = {e.get('source') for e in edges}
        if flow.entry_node_id and flow.entry_node_id not in keys:
            errors.append('نود ورودی نامعتبر است.')
        for edge in edges:
            if edge.get('source') not in keys or edge.get('target') not in keys:
                errors.append('اتصال به نود نامعتبر وجود دارد.')
                break
        orphans = [k for k in keys if k not in targets and k != flow.entry_node_id and k not in sources]
        if orphans:
            errors.append(f'نودهای بدون اتصال: {len(orphans)}')
        from instagram.automation.services.safe_templates import validate_template

        for node in nodes_data:
            node_type = node.get('type') or ''
            node_key = node.get('id') or node.get('key') or ''
            config = node.get('config') or {}
            if node_type not in SUPPORTED_NODE_TYPES:
                errors.append(f'نوع نود پشتیبانی‌نشده: {node_type}')
                continue
            if node_type in ('send_text', 'send_product'):
                template = str(config.get('template') or config.get('text') or '')
                errors.extend(validate_template(template))
            if node_key not in sources and node_type != 'stop':
                errors.append(f'نود بدون خروجی: {node_key}')
        return errors

    keys = {n.node_key for n in nodes}
    if flow.entry_node_id and flow.entry_node_id not in keys:
        errors.append('نود ورودی نامعتبر است.')
    out_map: dict[str, list[str]] = {n.node_key: [] for n in nodes}
    for edge in flow.edges.select_related('source_node', 'target_node'):
        out_map[edge.source_node.node_key].append(edge.target_node.node_key)
    # تشخیص حلقه ساده DFS
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in visiting:
            if len(path) > 20:
                errors.append('حلقهٔ خطرناک در فلو تشخیص داده شد.')
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in out_map.get(node, []):
            dfs(nxt, path + [nxt])
        visiting.discard(node)
        visited.add(node)

    if flow.entry_node_id:
        dfs(flow.entry_node_id, [flow.entry_node_id])
    for n in nodes:
        if n.node_type not in SUPPORTED_NODE_TYPES:
            errors.append(f'نوع نود پشتیبانی‌نشده: {n.node_type}')
        if n.node_type in ('send_text', 'send_product'):
            from instagram.automation.services.safe_templates import validate_template

            template = str((n.config or {}).get('template') or (n.config or {}).get('text') or '')
            errors.extend(validate_template(template))
        if n.node_key not in out_map:
            continue
        if not out_map[n.node_key] and n.node_type not in ('stop', 'wait', 'ask_question'):
            errors.append(f'نود بدون خروجی: {n.node_key}')
    return errors


def start_flow_execution(
    *,
    flow: InstagramFlow,
    contact,
    conversation=None,
    is_test_mode: bool = False,
    variables: dict | None = None,
) -> InstagramFlowExecution:
    return InstagramFlowExecution.objects.create(
        workspace_id=flow.workspace_id,
        flow=flow,
        flow_version=flow.version,
        conversation=conversation,
        contact=contact,
        current_node_key=flow.entry_node_id or '',
        status=InstagramFlowExecution.Status.RUNNING,
        is_test_mode=is_test_mode,
        variables=variables or {},
        log=[{'at': timezone.now().isoformat(), 'event': 'started'}],
    )


@transaction.atomic
def execute_flow_step(execution: InstagramFlowExecution) -> InstagramFlowExecution:
    execution = (
        InstagramFlowExecution.objects.select_for_update()
        .get(pk=execution.pk)
    )
    if len(execution.log or []) >= 50:
        execution.status = InstagramFlowExecution.Status.FAILED
        execution.failure_reason_sanitized = 'flow_step_limit_exceeded'
        execution.save(update_fields=['status', 'failure_reason_sanitized'])
        return execution
    flow = execution.flow
    if execution.status not in (
        InstagramFlowExecution.Status.RUNNING,
        InstagramFlowExecution.Status.WAITING,
    ):
        return execution

    node = None
    if execution.current_node_key:
        node = flow.nodes.filter(node_key=execution.current_node_key).first()
    if node is None:
        # definition-based
        definition = flow.definition or {}
        nodes = {n.get('id') or n.get('key'): n for n in (definition.get('nodes') or [])}
        node_data = nodes.get(execution.current_node_key) or {}
        node_type = node_data.get('type') or 'stop'
        config = node_data.get('config') or {}
    else:
        node_type = node.node_type
        config = node.config or {}

    log_entry: dict[str, Any] = {
        'at': timezone.now().isoformat(),
        'node': execution.current_node_key,
        'type': node_type,
    }

    try:
        next_key = _run_node(execution, node_type, config, log_entry)
    except MetaAPIError as exc:
        execution.status = InstagramFlowExecution.Status.FAILED
        execution.failed_at = timezone.now()
        execution.failure_reason_sanitized = exc.message_fa
        log_entry['error'] = exc.internal_code
        execution.log = list(execution.log or []) + [log_entry]
        execution.save()
        return execution
    except Exception as exc:
        logger.exception('Flow execution error')
        execution.status = InstagramFlowExecution.Status.FAILED
        execution.failed_at = timezone.now()
        execution.failure_reason_sanitized = 'خطای داخلی اجرای فلو'
        log_entry['error'] = type(exc).__name__
        execution.log = list(execution.log or []) + [log_entry]
        execution.save()
        return execution

    execution.log = list(execution.log or []) + [log_entry]
    if next_key is None or node_type == 'stop':
        execution.status = InstagramFlowExecution.Status.COMPLETED
        execution.completed_at = timezone.now()
        execution.current_node_key = execution.current_node_key
    elif node_type in ('wait', 'ask_question', 'save_user_input'):
        execution.status = InstagramFlowExecution.Status.WAITING
        execution.current_node_key = next_key or execution.current_node_key
    else:
        execution.current_node_key = next_key
        execution.status = InstagramFlowExecution.Status.RUNNING
    execution.save()
    return execution


def _run_node(
    execution: InstagramFlowExecution,
    node_type: str,
    config: dict,
    log_entry: dict,
) -> str | None:
    conversation = execution.conversation
    contact = execution.contact
    connection = contact.connection

    if node_type in ('send_text', 'send_product') and not execution.is_test_mode:
        from instagram.automation.services.messaging_window import (
            MessagingWindowClosed,
            is_messaging_window_open,
        )
        if not is_messaging_window_open(conversation):
            raise MessagingWindowClosed('Meta messaging window is closed')
    if node_type == 'send_text':
        text = _absolute_public_urls(str(config.get('text') or ''))
        if execution.is_test_mode:
            log_entry['test'] = True
            log_entry['text'] = text[:100]
        elif text and conversation:
            client = client_for_connection(connection)
            result = client.send_text_message(
                ig_user_id=connection.instagram_account_id,
                recipient_id=contact.instagram_scoped_user_id,
                text=text,
                correlation_id=str(execution.id),
            )
            InstagramMessage.objects.create(
                workspace_id=execution.workspace_id,
                conversation=conversation,
                external_message_id=str(result.get('message_id') or ''),
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.AUTOMATION,
                message_type='text',
                text=text,
                delivery_status=InstagramMessage.DeliveryStatus.SENT,
                sent_at=timezone.now(),
            )
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'send_product':
        product_id = config.get('product_id') or execution.variables.get('source_product_id')
        from balebot.models import CatalogItem
        from instagram.automation.models import InstagramAutomationRule
        from instagram.automation.services.link_tracking import create_tracked_link
        from instagram.automation.services.product_context import storefront_for_workspace
        from instagram.automation.services.safe_templates import product_template_context, render_template

        storefront = storefront_for_workspace(execution.workspace_id)
        item = CatalogItem.objects.filter(
            pk=product_id,
            workspace_id=execution.workspace_id,
            is_active=True,
        ).first()
        if item and storefront and storefront.catalog_id:
            if item.platform != storefront.catalog.platform:
                item = None
        if not item or not storefront or not storefront.catalog_id or item.stock == 0:
            log_entry['error'] = 'product_unavailable'
            alt = _absolute_public_urls(
                str(config.get('fallback_text') or 'این محصول در حال حاضر در دسترس نیست.')
            )
            if not execution.is_test_mode and conversation:
                client = client_for_connection(connection)
                result = client.send_text_message(
                    ig_user_id=connection.instagram_account_id,
                    recipient_id=contact.instagram_scoped_user_id,
                    text=alt,
                    correlation_id=str(execution.id),
                )
                InstagramMessage.objects.create(
                    workspace_id=execution.workspace_id,
                    conversation=conversation,
                    external_message_id=str(result.get('message_id') or ''),
                    direction=InstagramMessage.Direction.OUTBOUND,
                    sender_type=InstagramMessage.SenderType.AUTOMATION,
                    message_type='text',
                    text=alt,
                    delivery_status=InstagramMessage.DeliveryStatus.SENT,
                    sent_at=timezone.now(),
                )
            return config.get('fallback_next') or _next_from_edges(
                execution.flow, execution.current_node_key, condition_key='unavailable'
            )
        target = f'/shop/{storefront.catalog.public_id}/?product={item.slug}'
        rule = InstagramAutomationRule.objects.filter(pk=execution.variables.get('rule_id')).first()
        tracked = create_tracked_link(
            workspace=connection.workspace,
            target_url=target,
            flow=execution.flow,
            rule=rule,
            contact=contact,
            product_id=item.pk,
            source_media_id=execution.variables.get('source_media_id'),
        )
        tracked_path = reverse('instagram:tracked_link', kwargs={'code': tracked.short_code})
        base_url = str(getattr(settings, 'BASE_URL', '') or '').strip().rstrip('/')
        checkout_url = f'{base_url}{tracked_path}' if base_url else tracked_path
        store_url = f'{base_url}{target}' if base_url else target
        template = str(config.get('template') or config.get('intro') or (
            '{{ product.title }}\nقیمت: {{ product.price }} ریال\nوضعیت: {{ product.stock_status }}\n{{ checkout_url }}'
        ))
        text = render_template(
            template,
            product_template_context(item, checkout_url=checkout_url, store_url=store_url),
        )
        text = _absolute_public_urls(text)
        if execution.is_test_mode:
            log_entry['product_id'] = item.pk
            log_entry['checkout_url'] = checkout_url
        elif conversation:
            client = client_for_connection(connection)
            result = client.send_text_message(
                ig_user_id=connection.instagram_account_id,
                recipient_id=contact.instagram_scoped_user_id,
                text=text,
                correlation_id=str(execution.id),
            )
            InstagramMessage.objects.create(
                workspace_id=execution.workspace_id,
                conversation=conversation,
                external_message_id=str(result.get('message_id') or ''),
                direction=InstagramMessage.Direction.OUTBOUND,
                sender_type=InstagramMessage.SenderType.AUTOMATION,
                message_type='product',
                text=text,
                delivery_status=InstagramMessage.DeliveryStatus.SENT,
                sent_at=timezone.now(),
            )
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'add_tag':
        tag_id = config.get('tag_id')
        if tag_id:
            from balebot.models import Tag

            tag = Tag.objects.filter(pk=tag_id, workspace_id=execution.workspace_id).first()
            if tag:
                contact.tags.add(tag)
                log_entry['tag_id'] = tag_id
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'pause_automation' and conversation:
        conversation.automation_paused_permanent = bool(config.get('permanent', True))
        minutes = int(config.get('minutes') or 0)
        if minutes:
            conversation.automation_paused_until = timezone.now() + timedelta(minutes=minutes)
            conversation.automation_paused_permanent = False
        conversation.mode = conversation.Mode.HUMAN
        conversation.save()
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'assign_agent' and conversation:
        uid = config.get('user_id')
        conversation.assigned_user_id = uid
        conversation.mode = conversation.Mode.HUMAN
        conversation.save(update_fields=['assigned_user_id', 'mode', 'updated_at'])
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'close_conversation' and conversation:
        conversation.status = conversation.Status.CLOSED
        conversation.close_reason = str(config.get('reason') or '')
        conversation.save(update_fields=['status', 'close_reason', 'updated_at'])
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'add_internal_note' and conversation:
        InstagramMessage.objects.create(
            workspace_id=execution.workspace_id,
            conversation=conversation,
            direction=InstagramMessage.Direction.OUTBOUND,
            sender_type=InstagramMessage.SenderType.SYSTEM,
            message_type='note',
            text=str(config.get('text') or ''),
            delivery_status=InstagramMessage.DeliveryStatus.SENT,
            is_internal_note=True,
            sent_at=timezone.now(),
        )
        return _next_from_edges(execution.flow, execution.current_node_key)

    if node_type == 'condition':
        # ساده: متغیرها
        key = config.get('variable')
        expected = config.get('equals')
        actual = (execution.variables or {}).get(key)
        cond = 'yes' if actual == expected else 'no'
        return _next_from_edges(execution.flow, execution.current_node_key, condition_key=cond)

    if node_type == 'stop':
        return None

    raise ValueError(f'Unsupported flow node: {node_type}')


def _next_from_edges(flow: InstagramFlow, node_key: str, condition_key: str = '') -> str | None:
    edges = list(
        flow.edges.filter(source_node__node_key=node_key).order_by('priority', 'id')
    )
    if edges:
        if condition_key:
            for e in edges:
                if e.condition_key == condition_key:
                    return e.target_node.node_key
        return edges[0].target_node.node_key
    definition = flow.definition or {}
    for e in definition.get('edges') or []:
        if e.get('source') == node_key:
            if condition_key and e.get('condition') and e.get('condition') != condition_key:
                continue
            return e.get('target')
    return None


def publish_flow(flow: InstagramFlow) -> InstagramFlow:
    errors = validate_flow(flow)
    if errors:
        raise ValueError('; '.join(errors))
    # آرشیو نسخهٔ فعال قبلی هم‌نام
    InstagramFlow.objects.filter(
        workspace_id=flow.workspace_id,
        name=flow.name,
        status=InstagramFlow.Status.ACTIVE,
    ).exclude(pk=flow.pk).update(status=InstagramFlow.Status.ARCHIVED)
    flow.status = InstagramFlow.Status.ACTIVE
    flow.published_at = timezone.now()
    flow.save(update_fields=['status', 'published_at', 'updated_at'])
    return flow
