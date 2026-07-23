from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from balebot.models import CatalogItem, CatalogOrder


from instagram.automation.models import (
    InstagramConnection,
    InstagramConversation,
    InstagramFlowExecution,
    InstagramMessage,
    InstagramWebhookEvent,
    InstagramAutomationRule,
)


def connection_health(workspace) -> dict:
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    connections = list(
        InstagramConnection.objects.filter(workspace=workspace).order_by('-updated_at')[:20]
    )
    queue_lag = InstagramWebhookEvent.objects.filter(
        workspace=workspace,
        processing_status__in=[
            InstagramWebhookEvent.ProcessingStatus.QUEUED,
            InstagramWebhookEvent.ProcessingStatus.FAILED,
        ],
    ).count()
    errors_24h = InstagramWebhookEvent.objects.filter(
        workspace=workspace,
        processing_status__in=[
            InstagramWebhookEvent.ProcessingStatus.FAILED,
            InstagramWebhookEvent.ProcessingStatus.DEAD,
        ],
        failed_at__gte=day_ago,
    ).count()
    last_webhook = (
        InstagramWebhookEvent.objects.filter(workspace=workspace)
        .order_by('-received_at')
        .values_list('received_at', flat=True)
        .first()
    )
    last_out = (
        InstagramMessage.objects.filter(
            workspace=workspace,
            direction=InstagramMessage.Direction.OUTBOUND,
            delivery_status=InstagramMessage.DeliveryStatus.SENT,
        )
        .order_by('-sent_at')
        .values_list('sent_at', flat=True)
        .first()
    )
    return {
        'connections': [
            {
                'id': c.id,
                'username': c.username,
                'status': c.connection_status,
                'webhook_status': c.webhook_status,
                'token_expires_at': c.token_expires_at,
                'last_error': c.last_error_message_sanitized,
                'last_webhook_at': c.last_webhook_at,
            }
            for c in connections
        ],
        'queue_lag': queue_lag,
        'errors_24h': errors_24h,
        'last_webhook_at': last_webhook,
        'last_outbound_at': last_out,
    }


def analytics_summary(workspace, *, since=None, until=None, connection_id=None) -> dict:
    since = since or (timezone.now() - timedelta(days=7))
    until = until or timezone.now()
    msg_qs = InstagramMessage.objects.filter(
        workspace=workspace,
        created_at__gte=since,
        created_at__lte=until,
    )
    conv_qs = InstagramConversation.objects.filter(
        workspace=workspace,
        created_at__gte=since,
        created_at__lte=until,
    )
    if connection_id:
        msg_qs = msg_qs.filter(conversation__connection_id=connection_id)
        conv_qs = conv_qs.filter(connection_id=connection_id)

    exec_qs = InstagramFlowExecution.objects.filter(
        workspace=workspace,
        started_at__gte=since,
        started_at__lte=until,
    )
    sales = sales_attribution(workspace, since=since, until=until)
    return {
        'new_conversations': conv_qs.count(),
        'inbound_messages': msg_qs.filter(direction='inbound', is_internal_note=False).count(),
        'outbound_messages': msg_qs.filter(direction='outbound', is_internal_note=False).count(),
        'automation_replies': msg_qs.filter(sender_type='automation').count(),
        'agent_replies': msg_qs.filter(sender_type='agent').count(),
        'flows_started': exec_qs.count(),
        'flows_completed': exec_qs.filter(status='completed').count(),
        'flows_failed': exec_qs.filter(status='failed').count(),
        'human_takeovers': conv_qs.filter(mode='human').count(),
        'rules_executed': InstagramAutomationRule.objects.filter(
            workspace=workspace,
            last_executed_at__gte=since,
        ).aggregate(s=Count('id'))['s'] or 0,
        'meta_errors': InstagramWebhookEvent.objects.filter(
            workspace=workspace,
            processing_status__in=['failed', 'dead'],
            failed_at__gte=since,
        ).count(),
        'instagram_orders': sales['orders'],
        'instagram_paid_orders': sales['paid_orders'],
        'instagram_revenue_rial': sales['revenue_rial'],
    }


def sales_attribution(workspace, *, since=None, until=None) -> dict:
    since = since or (timezone.now() - timedelta(days=7))
    until = until or timezone.now()
    orders = CatalogOrder.objects.filter(
        workspace=workspace,
        source_channel=CatalogOrder.SourceChannel.INSTAGRAM,
        created_at__gte=since,
        created_at__lte=until,
    )
    paid = orders.filter(status=CatalogOrder.Status.PAID)
    rows = list(
        paid.values(
            'instagram_tracked_link__rule__name',
            'instagram_tracked_link__source_media__external_media_id',
            'instagram_tracked_link__source_media__media_type',
            'instagram_tracked_link__product_id',
        )
        .annotate(order_count=Count('id'), revenue_rial=Sum('total_amount'))
        .order_by('-revenue_rial', '-order_count')[:50]
    )
    product_ids = {
        row['instagram_tracked_link__product_id']
        for row in rows
        if row['instagram_tracked_link__product_id']
    }
    product_titles = dict(
        CatalogItem.objects.filter(workspace=workspace, pk__in=product_ids).values_list('pk', 'title')
    )
    attribution_rows = []
    for row in rows:
        product_id = row['instagram_tracked_link__product_id']
        attribution_rows.append({
            'rule': row['instagram_tracked_link__rule__name'] or 'بدون قانون',
            'media_id': row['instagram_tracked_link__source_media__external_media_id'] or '—',
            'media_type': row['instagram_tracked_link__source_media__media_type'] or '—',
            'product': product_titles.get(product_id, '—'),
            'order_count': row['order_count'],
            'revenue_rial': row['revenue_rial'] or 0,
        })
    return {
        'orders': orders.count(),
        'paid_orders': paid.count(),
        'revenue_rial': paid.aggregate(total=Sum('total_amount'))['total'] or 0,
        'rows': attribution_rows,
    }
