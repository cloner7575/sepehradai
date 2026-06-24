"""تعریف رفتار انواع آیتم مینی‌اپ."""

from __future__ import annotations

from balebot.models import CatalogItem

ITEM_TYPE_GUIDES: dict[str, dict[str, str | bool]] = {
    CatalogItem.ItemType.PRODUCT: {
        'label': 'محصول',
        'summary': 'فروش کالا یا محصول دیجیتال با قیمت، سبد خرید و پرداخت آنلاین.',
        'show_commerce': True,
        'show_download_block': False,
        'media_hint': 'تصاویر محصول را برای لیست و صفحه جزئیات آپلود کنید.',
        'default_sale_mode': CatalogItem.SaleMode.BOTH,
    },
    CatalogItem.ItemType.DOWNLOAD: {
        'label': 'فایل دانلود',
        'summary': 'ارائه فایل رایگان (PDF، ZIP و…) با دکمه دانلود مستقیم.',
        'show_commerce': False,
        'show_download_block': True,
        'media_hint': 'تصویر کاور اختیاری است؛ فایل اصلی را در بخش دانلود بارگذاری کنید.',
        'default_sale_mode': CatalogItem.SaleMode.REQUEST_ONLY,
    },
    CatalogItem.ItemType.VIDEO: {
        'label': 'ویدیو و آموزش',
        'summary': 'دوره، ویدیو آموزشی یا محتوای ویدیویی — با درخواست ثبت‌نام یا فروش دوره.',
        'show_commerce': True,
        'show_download_block': False,
        'media_hint': 'ویدیوها و تصاویر دوره را در گالری رسانه بارگذاری کنید.',
        'default_sale_mode': CatalogItem.SaleMode.REQUEST_ONLY,
    },
    CatalogItem.ItemType.SHOWCASE: {
        'label': 'معرفی و نمونه‌کار',
        'summary': 'ویترین نمونه‌کار، گالری پروژه یا معرفی بدون فروش مستقیم — فقط درخواست تماس.',
        'show_commerce': False,
        'show_download_block': False,
        'media_hint': 'تصاویر و ویدیوهای نمونه‌کار را در گالری رسانه بگذارید.',
        'default_sale_mode': CatalogItem.SaleMode.REQUEST_ONLY,
    },
}


def get_item_type_guide(item_type: str) -> dict[str, str | bool]:
    return ITEM_TYPE_GUIDES.get(item_type, ITEM_TYPE_GUIDES[CatalogItem.ItemType.PRODUCT])


def item_type_choices_for_form() -> list[tuple[str, str]]:
    return [(key, str(guide['label'])) for key, guide in ITEM_TYPE_GUIDES.items()]
