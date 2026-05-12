from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from balebot.models import Campaign, Subscriber


def resolve_campaign_subscribers_qs(campaign: Campaign) -> QuerySet[Subscriber]:
    qs = Subscriber.objects.filter(is_active=True, is_registered=True)
    tag_ids = list(campaign.target_tags.values_list('id', flat=True))
    if tag_ids:
        qs = qs.filter(tags__id__in=tag_ids).distinct()
    return qs.order_by('id')


def snapshot_campaign_audience(campaign: Campaign) -> list[int]:
    subscriber_ids = list(resolve_campaign_subscribers_qs(campaign).values_list('id', flat=True))
    campaign.audience_snapshot = subscriber_ids
    campaign.audience_snapshot_at = timezone.now()
    campaign.save(update_fields=['audience_snapshot', 'audience_snapshot_at', 'updated_at'])
    return subscriber_ids

