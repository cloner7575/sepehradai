"""کپی تنظیمات، فروشگاه و کمپین بین پلتفرم‌های بله و تلگرام."""

from __future__ import annotations

import copy
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

from balebot.models import (
    BotSettings,
    Campaign,
    CatalogCategory,
    CatalogItem,
    CatalogItemMedia,
    CatalogSettings,
    FlowMedia,
    Platform,
    Tag,
    Workspace,
)

_BOT_SETTINGS_SKIP = frozenset({
    'id',
    'pk',
    'bot_token',
    'webhook_secret',
    'webhook_public_url',
    'platform',
    'workspace',
    'workspace_id',
    'updated_at',
})

_CATALOG_SETTINGS_SKIP = frozenset({
    'id',
    'pk',
    'public_id',
    'platform',
    'workspace',
    'workspace_id',
    'admin_notify_chat_id',
    'created_at',
    'updated_at',
})


@dataclass
class PlatformSyncResult:
    bot_settings: bool = False
    flow_media: int = 0
    catalog_settings: bool = False
    categories: int = 0
    items: int = 0
    tags: int = 0
    campaigns: int = 0
    errors: list[str] = field(default_factory=list)


def _normalize_platform(platform: str) -> str:
    return Platform.TELEGRAM if platform == Platform.TELEGRAM else Platform.BALE


def _other_platform(platform: str) -> str:
    return Platform.TELEGRAM if platform == Platform.BALE else Platform.BALE


def _copy_file_field(instance, field_name: str, source_file) -> None:
    dest = getattr(instance, field_name)
    if not source_file:
        if dest:
            dest.delete(save=False)
        return
    source_file.open('rb')
    try:
        name = os.path.basename(source_file.name)
        dest.save(name, ContentFile(source_file.read()), save=False)
    finally:
        source_file.close()


def _collect_media_ids(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        mid = node.get('media_id')
        if mid:
            found.add(str(mid).strip())
        for value in node.values():
            found.update(_collect_media_ids(value))
    elif isinstance(node, list):
        for item in node:
            found.update(_collect_media_ids(item))
    return found


def _remap_media_ids(node: Any, mapping: dict[str, str]) -> Any:
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == 'media_id' and str(value).strip() in mapping:
                out[key] = mapping[str(value).strip()]
            else:
                out[key] = _remap_media_ids(value, mapping)
        return out
    if isinstance(node, list):
        return [_remap_media_ids(item, mapping) for item in node]
    return node


def _clone_flow_media(
    workspace: Workspace,
    source_platform: str,
    target_platform: str,
    media_ids: set[str],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not media_ids:
        return mapping
    qs = FlowMedia.objects.filter(
        workspace=workspace,
        platform=source_platform,
        pk__in=[mid for mid in media_ids if mid],
    )
    for media in qs:
        clone = FlowMedia(
            workspace=workspace,
            platform=target_platform,
            media_kind=media.media_kind,
            messenger_file_id='',
        )
        _copy_file_field(clone, 'file', media.file)
        clone.save()
        mapping[str(media.pk)] = str(clone.pk)
    return mapping


def _copy_bot_settings(
    workspace: Workspace,
    source: str,
    target: str,
    result: PlatformSyncResult,
) -> None:
    src = BotSettings.get_for_platform(workspace, source)
    dst = BotSettings.get_for_platform(workspace, target)

    preserve_token = dst.bot_token
    preserve_secret = dst.webhook_secret
    preserve_webhook_url = dst.webhook_public_url

    flow = copy.deepcopy(src.start_flow or {})
    media_ids = _collect_media_ids(flow)
    FlowMedia.objects.filter(workspace=workspace, platform=target).delete()
    media_map = _clone_flow_media(workspace, source, target, media_ids)
    result.flow_media = len(media_map)
    if flow:
        flow = _remap_media_ids(flow, media_map)

    for f in BotSettings._meta.get_fields():
        if not getattr(f, 'concrete', False) or getattr(f, 'many_to_many', False):
            continue
        name = f.name
        if name in _BOT_SETTINGS_SKIP:
            continue
        if name == 'start_flow':
            setattr(dst, name, flow)
            continue
        setattr(dst, name, getattr(src, name))

    dst.bot_token = preserve_token
    dst.webhook_secret = preserve_secret
    dst.webhook_public_url = preserve_webhook_url
    dst.save()
    result.bot_settings = True


def _copy_catalog_settings(
    workspace: Workspace,
    source: str,
    target: str,
    result: PlatformSyncResult,
) -> None:
    src = CatalogSettings.get_for_platform(workspace, source)
    dst = CatalogSettings.get_for_platform(workspace, target)

    for f in CatalogSettings._meta.get_fields():
        if not getattr(f, 'concrete', False) or getattr(f, 'many_to_many', False):
            continue
        name = f.name
        if name in _CATALOG_SETTINGS_SKIP:
            continue
        if name in ('logo', 'hero_background'):
            continue
        setattr(dst, name, getattr(src, name))

    _copy_file_field(dst, 'logo', src.logo)
    _copy_file_field(dst, 'hero_background', src.hero_background)
    dst.save()
    result.catalog_settings = True


def _copy_catalog_tree(
    workspace: Workspace,
    source: str,
    target: str,
    result: PlatformSyncResult,
) -> None:
    CatalogItem.objects.filter(workspace=workspace, platform=target).delete()
    CatalogCategory.objects.filter(workspace=workspace, platform=target).delete()

    cat_map: dict[int, int] = {}
    source_cats = list(
        CatalogCategory.objects.filter(workspace=workspace, platform=source).order_by('sort_order', 'name')
    )
    pending = list(source_cats)
    while pending:
        progress = False
        next_pass: list[CatalogCategory] = []
        for cat in pending:
            if cat.parent_id and cat.parent_id not in cat_map:
                next_pass.append(cat)
                continue
            new_cat = CatalogCategory(
                workspace=workspace,
                platform=target,
                parent_id=cat_map.get(cat.parent_id) if cat.parent_id else None,
                name=cat.name,
                slug=cat.slug,
                icon=cat.icon,
                sort_order=cat.sort_order,
                is_active=cat.is_active,
            )
            _copy_file_field(new_cat, 'image', cat.image)
            new_cat.save()
            cat_map[cat.id] = new_cat.id
            result.categories += 1
            progress = True
        if not progress and next_pass:
            for cat in next_pass:
                new_cat = CatalogCategory(
                    workspace=workspace,
                    platform=target,
                    parent=None,
                    name=cat.name,
                    slug=cat.slug,
                    icon=cat.icon,
                    sort_order=cat.sort_order,
                    is_active=cat.is_active,
                )
                _copy_file_field(new_cat, 'image', cat.image)
                new_cat.save()
                cat_map[cat.id] = new_cat.id
                result.categories += 1
            break
        pending = next_pass

    for item in CatalogItem.objects.filter(workspace=workspace, platform=source).prefetch_related('media'):
        new_item = CatalogItem(
            workspace=workspace,
            canonical_key=item.canonical_key,
            platform=target,
            category_id=cat_map.get(item.category_id) if item.category_id else None,
            title=item.title,
            slug=item.slug,
            short_description=item.short_description,
            description=item.description,
            item_type=item.item_type,
            price=item.price,
            sale_mode=item.sale_mode,
            stock=item.stock,
            download_link=item.download_link,
            metadata=copy.deepcopy(item.metadata or {}),
            is_active=item.is_active,
            is_featured=item.is_featured,
            sort_order=item.sort_order,
        )
        _copy_file_field(new_item, 'cover', item.cover)
        _copy_file_field(new_item, 'download_file', item.download_file)
        new_item.save()
        for media in item.media.all():
            new_media = CatalogItemMedia(
                item=new_item,
                media_type=media.media_type,
                title=media.title,
                sort_order=media.sort_order,
            )
            _copy_file_field(new_media, 'file', media.file)
            new_media.save()
        result.items += 1


def _copy_tags(workspace: Workspace, source: str, target: str, result: PlatformSyncResult) -> dict[str, int]:
    slug_to_target_id: dict[str, int] = {}
    Tag.objects.filter(workspace=workspace, platform=target).delete()
    for tag in Tag.objects.filter(workspace=workspace, platform=source):
        new_tag = Tag.objects.create(
            workspace=workspace,
            platform=target,
            name=tag.name,
            slug=tag.slug,
            tag_type=tag.tag_type,
            is_active=tag.is_active,
        )
        slug_to_target_id[tag.slug] = new_tag.id
        result.tags += 1
    return slug_to_target_id


def _copy_campaigns(
    workspace: Workspace,
    source: str,
    target: str,
    tag_slug_map: dict[str, int],
    result: PlatformSyncResult,
) -> None:
    Campaign.objects.filter(workspace=workspace, platform=target).exclude(
        status__in=(Campaign.Status.SENDING, Campaign.Status.QUEUED),
    ).delete()

    for camp in Campaign.objects.filter(workspace=workspace, platform=source).prefetch_related('target_tags'):
        if camp.status in (Campaign.Status.SENDING, Campaign.Status.QUEUED):
            continue
        new_camp = Campaign(
            workspace=workspace,
            platform=target,
            title=camp.title,
            content_type=camp.content_type,
            body=camp.body,
            inline_keyboard=copy.deepcopy(camp.inline_keyboard or []),
            audience_snapshot=[],
            audience_snapshot_at=None,
            status=Campaign.Status.DRAFT,
            schedule_kind=camp.schedule_kind,
            scheduled_at=camp.scheduled_at,
            started_at=None,
            completed_at=None,
        )
        _copy_file_field(new_camp, 'media', camp.media)
        new_camp.save()
        tag_ids = []
        for tag in camp.target_tags.all():
            tid = tag_slug_map.get(tag.slug)
            if tid:
                tag_ids.append(tid)
        if tag_ids:
            new_camp.target_tags.set(tag_ids)
        result.campaigns += 1


@transaction.atomic
def sync_platform_data(
    workspace: Workspace,
    source_platform: str,
    target_platform: str,
    *,
    copy_bot: bool = True,
    copy_catalog: bool = True,
    copy_tags: bool = True,
    copy_campaigns: bool = True,
) -> PlatformSyncResult:
    source = _normalize_platform(source_platform)
    target = _normalize_platform(target_platform)
    if source == target:
        raise ValueError('پلتفرم مبدأ و مقصد نمی‌توانند یکسان باشند.')

    result = PlatformSyncResult()
    tag_slug_map: dict[str, int] = {}

    if copy_bot:
        _copy_bot_settings(workspace, source, target, result)
    if copy_catalog:
        _copy_catalog_settings(workspace, source, target, result)
        _copy_catalog_tree(workspace, source, target, result)
    if copy_tags:
        tag_slug_map = _copy_tags(workspace, source, target, result)
    elif copy_campaigns:
        for tag in Tag.objects.filter(workspace=workspace, platform=target):
            tag_slug_map[tag.slug] = tag.id
    if copy_campaigns:
        _copy_campaigns(workspace, source, target, tag_slug_map, result)

    return result
