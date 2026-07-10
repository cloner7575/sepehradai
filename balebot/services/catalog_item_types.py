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
        'summary': 'فایل قابل دانلود — رایگان یا فروش با قیمت؛ دسترسی پس از خرید.',
        'show_commerce': True,
        'show_download_block': True,
        'media_hint': 'تصویر کاور اختیاری است؛ فایل اصلی را در بخش دانلود بارگذاری کنید.',
        'default_sale_mode': CatalogItem.SaleMode.BOTH,
    },
    CatalogItem.ItemType.VIDEO: {
        'label': 'ویدیو و آموزش',
        'summary': 'ویدیو آموزشی — آپلود یا لینک؛ رایگان یا فروش با دسترسی پس از خرید.',
        'show_commerce': True,
        'show_download_block': False,
        'media_hint': 'ویدیوها را آپلود کنید یا لینک مستقیم mp4/webm وارد کنید.',
        'default_sale_mode': CatalogItem.SaleMode.BOTH,
    },
    CatalogItem.ItemType.COURSE: {
        'label': 'دوره آموزشی',
        'summary': 'مجموعه ویدیوهای آموزشی — با خرید دوره به همه قسمت‌ها دسترسی داده می‌شود.',
        'show_commerce': True,
        'show_download_block': False,
        'media_hint': 'کاور دوره را بارگذاری کنید؛ قسمت‌ها را در بخش اعضای دوره اضافه کنید.',
        'default_sale_mode': CatalogItem.SaleMode.BUYABLE,
    },
    CatalogItem.ItemType.PACKAGE: {
        'label': 'پکیج فایل',
        'summary': 'مجموعه فایل‌های دانلودی — با خرید پکیج به همه فایل‌ها دسترسی داده می‌شود.',
        'show_commerce': True,
        'show_download_block': False,
        'media_hint': 'کاور پکیج را بارگذاری کنید؛ فایل‌ها را در بخش اعضای پکیج اضافه کنید.',
        'default_sale_mode': CatalogItem.SaleMode.BUYABLE,
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
