from __future__ import annotations

from datetime import timedelta, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from instagram.automation.models import InstagramMedia
from instagram.automation.services.oauth import client_for_connection


def _timestamp(value):
    parsed = parse_datetime(str(value or ''))
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def _media_type(row: dict, *, story: bool) -> str:
    if story:
        return InstagramMedia.MediaType.STORY
    product_type = str(row.get('media_product_type') or '').upper()
    if product_type == 'REELS':
        return InstagramMedia.MediaType.REEL
    return str(row.get('media_type') or '')


@transaction.atomic
def sync_connection_media(connection) -> dict[str, int]:
    client = client_for_connection(connection)
    now = timezone.now()
    seen: set[str] = set()
    created = 0
    updated = 0

    sources = (
        (client.list_media(connection.instagram_account_id).get('data') or [], False),
        (client.list_stories(connection.instagram_account_id).get('data') or [], True),
    )
    for rows, is_story in sources:
        for row in rows:
            external_id = str(row.get('id') or '')
            if not external_id:
                continue
            seen.add(external_id)
            published = _timestamp(row.get('timestamp'))
            defaults = {
                'workspace_id': connection.workspace_id,
                'media_type': _media_type(row, story=is_story),
                'media_product_type': str(row.get('media_product_type') or ''),
                'caption': str(row.get('caption') or ''),
                'permalink': str(row.get('permalink') or ''),
                'media_url': str(row.get('media_url') or ''),
                'thumbnail_url': str(row.get('thumbnail_url') or ''),
                'published_at': published,
                'expires_at': (published + timedelta(hours=24)) if is_story and published else None,
                'is_active': True,
            }
            _, was_created = InstagramMedia.objects.update_or_create(
                connection=connection,
                external_media_id=external_id,
                defaults=defaults,
            )
            created += int(was_created)
            updated += int(not was_created)

    InstagramMedia.objects.filter(connection=connection, media_type=InstagramMedia.MediaType.STORY).filter(
        expires_at__lte=now,
    ).update(is_active=False)
    return {'created': created, 'updated': updated, 'seen': len(seen)}
