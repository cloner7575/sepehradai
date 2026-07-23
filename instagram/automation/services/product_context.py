from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from balebot.models import CatalogItem
from instagram.automation.models import InstagramMedia, InstagramStorefrontConfig


def normalize_media_url(value: str) -> str:
    try:
        parsed = urlsplit(str(value or '').strip())
    except ValueError:
        return ''
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return ''
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), '', ''))


def storefront_for_workspace(workspace_id: int):
    return InstagramStorefrontConfig.objects.select_related('catalog').filter(
        workspace_id=workspace_id,
        is_enabled=True,
        catalog__is_enabled=True,
    ).first()


def resolve_source_product(*, connection, event, rule=None):
    media = None
    source_id = str(event.media_id or event.story_id or '')
    if source_id:
        media = InstagramMedia.objects.select_related('product').filter(
            connection=connection,
            external_media_id=source_id,
            is_active=True,
        ).first()
    if not media and event.story_url:
        wanted = normalize_media_url(event.story_url)
        for candidate in InstagramMedia.objects.select_related('product').filter(
            connection=connection,
            is_active=True,
        ).exclude(permalink=''):
            if normalize_media_url(candidate.permalink) == wanted:
                media = candidate
                break
    if media and media.product_id and media.product.is_active:
        return media.product, media

    fallback_id = (rule.schedule or {}).get('product_id') if rule else None
    if not fallback_id:
        return None, media
    storefront = storefront_for_workspace(connection.workspace_id)
    qs = CatalogItem.objects.filter(
        pk=fallback_id,
        workspace_id=connection.workspace_id,
        is_active=True,
    )
    if storefront and storefront.catalog:
        qs = qs.filter(platform=storefront.catalog.platform)
    return qs.first(), media


def stock_status(item) -> str:
    if item.stock is None:
        return 'available'
    return 'in_stock' if item.stock > 0 else 'out_of_stock'
