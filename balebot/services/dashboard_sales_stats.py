"""آمار فروشگاه برای داشبورد — سری‌های زمانی و دادهٔ نمودار."""

from __future__ import annotations

from datetime import timedelta

import jdatetime
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from balebot.models import CatalogOrder, CatalogOrderLine, Subscriber
from balebot.services.catalog_currency import rial_to_toman


def _jalali_day_label(day) -> str:
    jd = jdatetime.date.fromgregorian(date=day)
    return jd.strftime('%m/%d')


def _daily_series(days: int) -> list:
    today = timezone.localdate()
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def build_sales_dashboard_stats(scope: dict, *, days: int = 30) -> dict:
    start_date = timezone.localdate() - timedelta(days=days - 1)
    day_list = _daily_series(days)
    day_labels = [_jalali_day_label(d) for d in day_list]

    orders_qs = CatalogOrder.objects.filter(**scope)
    paid_qs = orders_qs.filter(status=CatalogOrder.Status.PAID)
    week_ago = timezone.now() - timedelta(days=7)

    revenue_total = paid_qs.aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_week = (
        paid_qs.filter(updated_at__gte=week_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    )
    paid_count = paid_qs.count()
    paid_week = paid_qs.filter(updated_at__gte=week_ago).count()
    pending_count = orders_qs.filter(status=CatalogOrder.Status.PENDING).count()
    order_total = orders_qs.count()
    order_week = orders_qs.filter(created_at__gte=week_ago).count()

    aov_toman = rial_to_toman(revenue_total // paid_count) if paid_count else 0

    subscribers_qs = Subscriber.objects.filter(**scope)
    miniapp_visitors = subscribers_qs.filter(miniapp_first_seen_at__isnull=False).count()
    conversion_rate_pct = (
        round(paid_count * 100 / miniapp_visitors, 1) if miniapp_visitors else None
    )

    revenue_by_day = {
        row['day']: row['revenue'] or 0
        for row in (
            paid_qs.filter(updated_at__date__gte=start_date)
            .annotate(day=TruncDate('updated_at'))
            .values('day')
            .annotate(revenue=Sum('total_amount'))
        )
    }
    paid_count_by_day = {
        row['day']: row['c']
        for row in (
            paid_qs.filter(updated_at__date__gte=start_date)
            .annotate(day=TruncDate('updated_at'))
            .values('day')
            .annotate(c=Count('id'))
        )
    }
    orders_by_day = {
        row['day']: row['c']
        for row in (
            orders_qs.filter(created_at__date__gte=start_date)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(c=Count('id'))
        )
    }

    daily_revenue_toman = [
        rial_to_toman(revenue_by_day.get(d, 0)) or 0 for d in day_list
    ]
    daily_paid_count = [paid_count_by_day.get(d, 0) for d in day_list]
    daily_order_count = [orders_by_day.get(d, 0) for d in day_list]

    status_rows = orders_qs.values('status').annotate(c=Count('id')).order_by('-c')
    status_labels = []
    status_values = []
    status_map = dict(CatalogOrder.Status.choices)
    for row in status_rows:
        status_labels.append(status_map.get(row['status'], row['status']))
        status_values.append(row['c'])

    fulfillment_rows = (
        paid_qs.values('fulfillment_status')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    fulfillment_map = dict(CatalogOrder.FulfillmentStatus.choices)
    fulfillment_labels = []
    fulfillment_values = []
    for row in fulfillment_rows:
        key = row['fulfillment_status']
        fulfillment_labels.append(fulfillment_map.get(key, key))
        fulfillment_values.append(row['c'])

    top_items = list(
        CatalogOrderLine.objects.filter(
            order__workspace=scope['workspace'],
            order__platform=scope['platform'],
            order__status=CatalogOrder.Status.PAID,
        )
        .values('title_snapshot')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')[:6]
    )
    top_item_labels = [row['title_snapshot'][:28] for row in top_items]
    top_item_qty = [row['qty'] or 0 for row in top_items]

    preparing_count = paid_qs.filter(
        fulfillment_status=CatalogOrder.FulfillmentStatus.PREPARING,
    ).count()
    shipped_count = paid_qs.filter(
        fulfillment_status=CatalogOrder.FulfillmentStatus.SHIPPED,
    ).count()

    return {
        'revenue_total': revenue_total,
        'revenue_week': revenue_week,
        'revenue_month': sum(revenue_by_day.values()),
        'order_total': order_total,
        'order_week': order_week,
        'order_paid_total': paid_count,
        'order_paid_week': paid_week,
        'order_pending': pending_count,
        'order_aov_toman': aov_toman,
        'miniapp_visitors': miniapp_visitors,
        'conversion_rate_pct': conversion_rate_pct,
        'preparing_count': preparing_count,
        'shipped_count': shipped_count,
        'charts': {
            'daily_labels': day_labels,
            'daily_revenue_toman': daily_revenue_toman,
            'daily_order_count': daily_order_count,
            'daily_paid_count': daily_paid_count,
            'status_labels': status_labels,
            'status_values': status_values,
            'fulfillment_labels': fulfillment_labels,
            'fulfillment_values': fulfillment_values,
            'top_item_labels': top_item_labels,
            'top_item_qty': top_item_qty,
            'funnel_labels': ['بازدید مینی‌اپ', 'سفارش ثبت‌شده', 'پرداخت‌شده'],
            'funnel_values': [miniapp_visitors, order_total, paid_count],
        },
    }
