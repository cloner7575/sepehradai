"""دادهٔ انتخابگر دسته/محصول/برچسب برای ویرایشگر جریان و مینی‌اپ."""

from __future__ import annotations

from balebot.models import CatalogCategory, CatalogItem, Tag


def catalog_picker_json(scope: dict) -> dict[str, list[dict[str, str]]]:
    picker_categories = list(
        CatalogCategory.objects.filter(**scope, is_active=True)
        .select_related('parent')
        .order_by('sort_order', 'name')[:300]
    )
    picker_items = list(
        CatalogItem.objects.filter(**scope, is_active=True)
        .order_by('sort_order', 'title')[:500]
    )
    picker_tags = list(
        Tag.objects.filter(**scope, is_active=True).order_by('name')[:200]
    )
    return {
        'categories': [
            {
                'name': (
                    f'{c.parent.name} › {c.name}' if c.parent_id and c.parent else c.name
                ),
                'slug': c.slug,
            }
            for c in picker_categories
        ],
        'items': [
            {
                'title': i.title,
                'slug': i.slug,
            }
            for i in picker_items
        ],
        'tags': [
            {
                'name': t.name,
                'slug': t.slug,
            }
            for t in picker_tags
        ],
    }
