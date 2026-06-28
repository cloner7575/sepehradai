"""اعمال الگوهای آماده فروشگاه روی workspace+platform."""

from __future__ import annotations

import copy
import logging
from typing import Any, Literal

from django.db import transaction
from django.utils.text import slugify

from balebot.models import (
    BotSettings,
    Campaign,
    CatalogCategory,
    CatalogItem,
    CatalogSettings,
    DiscountCode,
    StoreTemplate,
    Workspace,
)
from balebot.services.flow_sanitize import sanitize_start_flow
from balebot.services.catalog_page_layout import sanitize_home_blocks

logger = logging.getLogger(__name__)

ApplyMode = Literal['append', 'replace']
ApplyScope = Literal['miniapp', 'bot']


def _replace_placeholders(obj: Any, replacements: dict[str, str]) -> Any:
    if isinstance(obj, str):
        out = obj
        for key, value in replacements.items():
            out = out.replace(key, value)
        return out
    if isinstance(obj, list):
        return [_replace_placeholders(item, replacements) for item in obj]
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, replacements) for k, v in obj.items()}
    return obj


def _normalize_text_node(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    if out.get('type') == 'text' and 'text' in out and 'body' not in out:
        out['body'] = out.pop('text')
    return out


def _normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    out = dict(action)
    if out.get('type') == 'text' and 'text' in out and 'body' not in out:
        out['body'] = out.pop('text')
    return out


def _normalize_button(btn: dict[str, Any]) -> dict[str, Any]:
    out = dict(btn)
    if 'label' in out and 'text' not in out:
        out['text'] = out['label']
    # label_slug فقط برای پردازش الگو است، نه برچسب‌گذاری مشترک.
    out.pop('label_slug', None)
    action = out.get('action')
    if isinstance(action, dict):
        out['action'] = _normalize_action(action)
    return out


def _normalize_flow_node(node: dict[str, Any]) -> dict[str, Any]:
    out = dict(node)
    ntype = str(out.get('type', '')).lower()
    if ntype == 'text':
        return _normalize_text_node(out)
    if ntype == 'sequence':
        items = []
        for item in out.get('items') or []:
            if isinstance(item, dict):
                items.append(_normalize_flow_node(item))
        out['items'] = items
        return out
    if ntype == 'buttons':
        rows = []
        for row in out.get('rows') or []:
            if not isinstance(row, list):
                continue
            rows.append([_normalize_button(btn) for btn in row if isinstance(btn, dict)])
        out['rows'] = rows
        return out
    return out


def prepare_start_flow(raw_flow: dict[str, Any], shop_url: str) -> dict[str, Any]:
    flow = copy.deepcopy(raw_flow or {})
    flow = _replace_placeholders(flow, {'{shop_url}': shop_url})
    root = flow.get('root')
    if isinstance(root, dict):
        flow['root'] = _normalize_flow_node(root)
    flow['version'] = 2
    return sanitize_start_flow(flow)


def _map_theme(theme: dict[str, Any]) -> dict[str, Any]:
    theme = theme or {}
    return {
        'primary_color': theme.get('primary') or theme.get('primary_color') or '#2563eb',
        'accent_color': theme.get('accent') or theme.get('accent_color') or '#7c3aed',
        'layout': theme.get('layout') or 'grid',
        'font_family': theme.get('font') or theme.get('font_family') or 'Vazirmatn',
    }


def _map_labels(labels: dict[str, Any]) -> dict[str, Any]:
    labels = labels or {}
    buy = (labels.get('buy') or labels.get('buy_now') or 'خرید').strip()
    cart = (labels.get('cart') or 'سبد خرید').strip()
    checkout = (labels.get('checkout') or 'تسویه حساب').strip()
    return {
        'buy_now': buy,
        'add_to_cart': (labels.get('add_to_cart') or buy).strip(),
        'request_quote': (labels.get('request_quote') or 'درخواست / تماس').strip(),
        'cart': cart,
        'checkout': checkout,
        'download': (labels.get('download') or 'دانلود').strip(),
        'remove_from_cart': (labels.get('remove_from_cart') or 'حذف').strip(),
    }


def _map_item_type(raw: str) -> str:
    value = (raw or 'product').strip().lower()
    if value in ('service', 'portfolio'):
        return CatalogItem.ItemType.SHOWCASE
    if value in dict(CatalogItem.ItemType.choices):
        return value
    return CatalogItem.ItemType.PRODUCT


def _map_sale_mode(raw: str, item_type: str) -> str:
    value = (raw or '').strip().lower()
    if item_type == CatalogItem.ItemType.SHOWCASE:
        return CatalogItem.SaleMode.REQUEST_ONLY
    if value in ('quote', 'request', 'request_only'):
        return CatalogItem.SaleMode.REQUEST_ONLY
    if value in ('buy', 'buyable'):
        return CatalogItem.SaleMode.BUYABLE
    if value in dict(CatalogItem.SaleMode.choices):
        return value
    return CatalogItem.SaleMode.BOTH


def _clear_catalog_content(workspace: Workspace, platform: str) -> None:
    CatalogItem.objects.filter(workspace=workspace, platform=platform).delete()
    CatalogCategory.objects.filter(workspace=workspace, platform=platform).delete()


def _category_exists(workspace: Workspace, platform: str, slug: str) -> bool:
    return CatalogCategory.objects.filter(workspace=workspace, platform=platform, slug=slug).exists()


def _item_exists(workspace: Workspace, platform: str, slug: str) -> bool:
    return CatalogItem.objects.filter(workspace=workspace, platform=platform, slug=slug).exists()


@transaction.atomic
def apply_template(
    template: StoreTemplate,
    workspace: Workspace,
    platform: str,
    *,
    mode: ApplyMode = 'append',
    scope: ApplyScope = 'miniapp',
) -> dict[str, int]:
    """
    دادهٔ template.data را داخل workspace+platform مادی می‌کند.
    scope=miniapp: ویترین، دسته‌ها و محصولات
    scope=bot: جریان /start، تنظیمات ربات، تخفیف و کمپین نمونه
    """
    data = template.data or {}
    stats = {
        'categories_created': 0,
        'items_created': 0,
        'campaign_created': 0,
        'discount_created': 0,
        'bot_flow_applied': 0,
        'bot_settings_applied': 0,
    }

    if scope == 'miniapp':
        stats.update(_apply_miniapp_template(template, workspace, platform, data, mode=mode))
    elif scope == 'bot':
        stats.update(_apply_bot_template(template, workspace, platform, data, mode=mode))

    return stats


def _apply_miniapp_template(
    template: StoreTemplate,
    workspace: Workspace,
    platform: str,
    data: dict[str, Any],
    *,
    mode: ApplyMode,
) -> dict[str, int]:
    catalog = CatalogSettings.get_for_platform(workspace, platform)

    if mode == 'replace':
        _clear_catalog_content(workspace, platform)

    settings_data = data.get('settings') or {}
    catalog.hero_title = (settings_data.get('hero_title') or catalog.hero_title or '')[:200]
    catalog.hero_subtitle = (settings_data.get('hero_subtitle') or catalog.hero_subtitle or '')[:300]
    theme_patch = _map_theme(settings_data.get('theme') or {})
    home_blocks_raw = settings_data.get('home_blocks')
    if isinstance(home_blocks_raw, list) and home_blocks_raw:
        theme_patch['home_blocks'] = sanitize_home_blocks(home_blocks_raw)
    elif not (catalog.theme_config or {}).get('home_blocks'):
        from balebot.data.home_blocks_presets import build_home_blocks_for_template

        theme_patch['home_blocks'] = build_home_blocks_for_template(
            slug=template.slug,
            industry=template.industry,
            categories=data.get('categories') if isinstance(data.get('categories'), list) else [],
            marketing=data.get('marketing') if isinstance(data.get('marketing'), dict) else {},
            settings=settings_data,
        )
    catalog.theme_config = {**(catalog.theme_config or {}), **theme_patch}
    catalog.labels = {**(catalog.labels or {}), **_map_labels(settings_data.get('labels') or {})}
    catalog.save(update_fields=['hero_title', 'hero_subtitle', 'theme_config', 'labels', 'updated_at'])

    category_by_slug: dict[str, CatalogCategory] = {}
    categories_created = 0
    for row in data.get('categories') or []:
        if not isinstance(row, dict):
            continue
        slug = (row.get('slug') or slugify(row.get('name') or ''))[:140]
        if not slug:
            continue
        if mode == 'append' and _category_exists(workspace, platform, slug):
            category_by_slug[slug] = CatalogCategory.objects.get(
                workspace=workspace, platform=platform, slug=slug,
            )
            continue
        parent_slug = row.get('parent')
        parent = category_by_slug.get(parent_slug) if parent_slug else None
        cat, created = CatalogCategory.objects.get_or_create(
            workspace=workspace,
            platform=platform,
            slug=slug,
            defaults={
                'name': (row.get('name') or slug)[:120],
                'icon': (row.get('icon') or '')[:64],
                'sort_order': int(row.get('sort_order') or 0),
                'parent': parent,
                'is_active': True,
            },
        )
        if not created and mode == 'replace':
            cat.name = (row.get('name') or slug)[:120]
            cat.icon = (row.get('icon') or '')[:64]
            cat.sort_order = int(row.get('sort_order') or 0)
            cat.parent = parent
            cat.is_active = True
            cat.save()
        category_by_slug[slug] = cat
        if created:
            categories_created += 1

    items_created = 0
    for row in data.get('items') or []:
        if not isinstance(row, dict):
            continue
        slug = (row.get('slug') or slugify(row.get('name') or ''))[:220]
        if not slug:
            continue
        if mode == 'append' and _item_exists(workspace, platform, slug):
            continue
        cat_slug = row.get('category') or ''
        category = category_by_slug.get(cat_slug)
        if not category and cat_slug:
            category = CatalogCategory.objects.filter(
                workspace=workspace, platform=platform, slug=cat_slug,
            ).first()
        item_type = _map_item_type(row.get('item_type') or 'product')
        sale_mode = _map_sale_mode(row.get('sale_mode') or 'buy', item_type)
        price_raw = row.get('price')
        price = int(price_raw) if price_raw not in (None, '') else None
        if item_type == CatalogItem.ItemType.SHOWCASE and sale_mode == CatalogItem.SaleMode.REQUEST_ONLY:
            price = price if price and price > 0 else None
        stock = row.get('stock')
        stock_val = int(stock) if stock is not None else None
        CatalogItem.objects.create(
            workspace=workspace,
            platform=platform,
            category=category,
            title=(row.get('name') or slug)[:200],
            slug=slug,
            description=(row.get('description') or '')[:5000],
            item_type=item_type,
            sale_mode=sale_mode,
            price=price,
            compare_at_price=int(row['compare_at_price']) if row.get('compare_at_price') not in (None, '') else None,
            sales_count=max(0, int(row.get('sales_count') or 0)),
            stock=stock_val,
            is_featured=bool(row.get('is_featured')),
            is_active=True,
        )
        items_created += 1

    return {
        'categories_created': categories_created,
        'items_created': items_created,
        'campaign_created': 0,
        'discount_created': 0,
        'bot_flow_applied': 0,
        'bot_settings_applied': 0,
    }


def _apply_bot_template(
    template: StoreTemplate,
    workspace: Workspace,
    platform: str,
    data: dict[str, Any],
    *,
    mode: ApplyMode,
) -> dict[str, int]:
    catalog = CatalogSettings.get_for_platform(workspace, platform)
    bot = BotSettings.get_for_platform(workspace, platform)
    shop_url = catalog.build_mini_app_url(bot) or f'/shop/{catalog.public_id}/'

    bot_flow_applied = 0
    start_flow = data.get('start_flow')
    if isinstance(start_flow, dict) and start_flow.get('root'):
        bot.start_flow = prepare_start_flow(start_flow, shop_url)
        bot.save(update_fields=['start_flow', 'updated_at'])
        bot_flow_applied = 1

    bot_settings_applied = 0
    bot_settings = data.get('bot_settings') or {}
    if isinstance(bot_settings, dict) and bot_settings:
        bot_fields: list[str] = []
        if 'collect_contact_on_start' in bot_settings:
            bot.collect_contact_on_start = bool(bot_settings['collect_contact_on_start'])
            bot_fields.append('collect_contact_on_start')
        contact_msg = (bot_settings.get('start_message_contact') or '').strip()
        if contact_msg:
            bot.start_message_contact = contact_msg[:4096]
            bot_fields.append('start_message_contact')
        if bot_fields:
            bot_fields.append('updated_at')
            bot.save(update_fields=bot_fields)
            bot_settings_applied = 1

    marketing = data.get('marketing') or {}
    discount_created = 0
    if isinstance(marketing, dict):
        welcome = marketing.get('welcome_discount') or {}
        if isinstance(welcome, dict) and (welcome.get('code') or '').strip():
            code = (welcome['code'] or '').strip().upper()[:40]
            kind_raw = (welcome.get('kind') or 'percent').strip().lower()
            kind = (
                DiscountCode.Kind.AMOUNT
                if kind_raw == 'amount'
                else DiscountCode.Kind.PERCENT
            )
            value = int(welcome.get('value') or 0)
            if code and value > 0:
                _, created = DiscountCode.objects.update_or_create(
                    workspace=workspace,
                    platform=platform,
                    code=code,
                    defaults={
                        'kind': kind,
                        'value': value,
                        'is_active': True,
                    },
                )
                if created:
                    discount_created = 1

    campaign_created = 0
    campaign_rows: list[dict] = []
    if isinstance(marketing, dict):
        for row in marketing.get('campaigns') or []:
            if isinstance(row, dict) and (row.get('title') or '').strip():
                campaign_rows.append(row)
    if not campaign_rows:
        sample = data.get('sample_campaign') or {}
        if isinstance(sample, dict) and (sample.get('title') or '').strip():
            campaign_rows.append(sample)

    for campaign_data in campaign_rows:
        title = (campaign_data.get('title') or '').strip()[:255]
        if not title:
            continue
        exists = Campaign.objects.filter(
            workspace=workspace,
            platform=platform,
            title=title,
            status=Campaign.Status.DRAFT,
        ).exists()
        if exists and mode != 'replace':
            continue
        if exists and mode == 'replace':
            Campaign.objects.filter(
                workspace=workspace,
                platform=platform,
                title=title,
                status=Campaign.Status.DRAFT,
            ).delete()
        Campaign.objects.create(
            workspace=workspace,
            platform=platform,
            title=title,
            content_type=Campaign.ContentType.TEXT,
            body=(campaign_data.get('body') or '')[:4096],
            status=Campaign.Status.DRAFT,
        )
        campaign_created += 1

    return {
        'categories_created': 0,
        'items_created': 0,
        'campaign_created': campaign_created,
        'discount_created': discount_created,
        'bot_flow_applied': bot_flow_applied,
        'bot_settings_applied': bot_settings_applied,
    }
