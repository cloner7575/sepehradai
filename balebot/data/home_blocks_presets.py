"""چیدمان پیش‌فرض صفحهٔ اصلی مینی‌اپ برای هر الگوی فروشگاه."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from django.utils import timezone

from balebot.services.catalog_page_layout import sanitize_home_blocks

# متن و FAQ به تفکیک صنف
_INDUSTRY_COPY: dict[str, dict[str, Any]] = {
    'clothing': {
        'announcement': '🚚 ارسال رایگان برای سفارش‌های بالای ۵ میلیون تومان',
        'countdown_title': 'حراج آخر هفته',
        'carousel_source': 'bestselling',
        'carousel_title': 'پرفروش‌ترین‌ها',
        'trust': [
            {'icon': '✅', 'label': 'اصالت کالا'},
            {'icon': '🔄', 'label': '۷ روز تعویض سایز'},
            {'icon': '🚚', 'label': 'ارسال سریع'},
            {'icon': '💬', 'label': 'مشاوره استایل'},
        ],
        'faq': [
            {'q': 'هزینه ارسال چقدره؟', 'a': 'برای سفارش‌های بالای ۵ میلیون ارسال رایگان است؛ در غیر این صورت هزینه بر اساس شهر محاسبه می‌شود.'},
            {'q': 'امکان تعویض سایز هست؟', 'a': 'تا ۷ روز پس از تحویل، در صورت سالم بودن برچسب، تعویض سایز یا رنگ امکان‌پذیر است.'},
            {'q': 'چند روز طول می‌کشه برسه؟', 'a': 'معمولاً ۲ تا ۵ روز کاری بسته به شهر مقصد.'},
        ],
        'testimonials': [
            {'name': 'مریم', 'text': 'کیفیت پارچه عالی بود، دقیقاً مثل عکس رسید.', 'rating': 5},
            {'name': 'سارا', 'text': 'سایزبندی درست بود و ارسال سریع انجام شد.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۱۰ تا ۲۱ — جمعه ۱۶ تا ۲۱',
    },
    'food': {
        'announcement': '🍰 سفارش‌های امروز تا ساعت ۱۸ آماده ارسال می‌شوند',
        'countdown_title': 'پیشنهاد ویژه امروز',
        'carousel_source': 'featured',
        'carousel_title': 'محبوب‌ترین‌ها',
        'trust': [
            {'icon': '🌿', 'label': 'مواد تازه'},
            {'icon': '🧊', 'label': 'بسته‌بندی بهداشتی'},
            {'icon': '🚚', 'label': 'ارسال سرد'},
            {'icon': '⭐', 'label': 'رضایت مشتری'},
        ],
        'faq': [
            {'q': 'ارسال به چه شهرهایی دارید؟', 'a': 'ارسال درون‌شهری و بین‌شهری بسته به نوع محصول؛ جزئیات را هنگام سفارش می‌بینید.'},
            {'q': 'محصولات چند روز ماندگاری دارند؟', 'a': 'بسته به نوع محصول؛ روی بسته‌بندی تاریخ مصرف درج می‌شود.'},
            {'q': 'سفارش سفارشی قبول می‌کنید؟', 'a': 'بله، برای کیک و غذای سفارشی حداقل ۲۴ ساعت قبل هماهنگ کنید.'},
        ],
        'testimonials': [
            {'name': 'نرگس', 'text': 'طعم خانگی واقعی داشت، حتماً دوباره سفارش می‌دم.', 'rating': 5},
        ],
        'hours': 'هر روز ۹ تا ۲۱ — سفارش سفارشی با هماهنگی قبلی',
    },
    'beauty': {
        'announcement': '✨ ارسال رایگان خرید بالای ۳ میلیون تومان',
        'countdown_title': 'فروش ویژه محصولات مراقبت',
        'carousel_source': 'discounted',
        'carousel_title': 'تخفیف‌دارها',
        'trust': [
            {'icon': '✅', 'label': 'اصالت کالا'},
            {'icon': '🧪', 'label': 'تاریخ معتبر'},
            {'icon': '🎁', 'label': 'هدیه‌پیچی رایگان'},
            {'icon': '💬', 'label': 'مشاوره پوست'},
        ],
        'faq': [
            {'q': 'محصولات اصل هستند؟', 'a': 'همه محصولات از نمایندگی‌های معتبر تهیه می‌شوند و ضمانت اصالت دارند.'},
            {'q': 'برای پوست حساس مناسب است؟', 'a': 'در توضیحات هر محصول نوع پوست مناسب ذکر شده؛ در صورت نیاز مشاوره بگیرید.'},
        ],
        'testimonials': [
            {'name': 'الهام', 'text': 'سرم ویتامین سی واقعاً پوستم رو روشن کرد.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۱۰ تا ۲۰',
    },
    'home': {
        'announcement': '🏠 ارسال رایگان سفارش‌های بالای ۴ میلیون تومان',
        'countdown_title': 'حراج فصلی دکور',
        'carousel_source': 'featured',
        'carousel_title': 'پیشنهاد ویژه',
        'trust': [
            {'icon': '🪴', 'label': 'گلدان سالم'},
            {'icon': '📦', 'label': 'بسته‌بندی ایمن'},
            {'icon': '🔄', 'label': '۷ روز مرجوعی'},
            {'icon': '💬', 'label': 'راهنمای نگهداری'},
        ],
        'faq': [
            {'q': 'گیاه با گلدان ارسال می‌شود؟', 'a': 'بله، گیاهان با گلدان و خاک مخصوص بسته‌بندی و ارسال می‌شوند.'},
            {'q': 'راهنمای نگهداری دارید؟', 'a': 'برای هر گیاه راهنمای آبیاری و نور همراه محصول ارسال می‌شود.'},
        ],
        'testimonials': [
            {'name': 'رضا', 'text': 'گیاه سالم رسید، بسته‌بندی عالی بود.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۹ تا ۱۹',
    },
    'tech': {
        'announcement': '📱 گارانتی اصالت + ارسال سریع به سراسر کشور',
        'countdown_title': 'پیشنهاد محدود هفته',
        'carousel_source': 'newest',
        'carousel_title': 'جدیدترین‌ها',
        'trust': [
            {'icon': '✅', 'label': 'اصالت کالا'},
            {'icon': '🛡️', 'label': 'گارانتی معتبر'},
            {'icon': '🚚', 'label': 'ارسال ۲۴ ساعته'},
            {'icon': '🔧', 'label': 'پشتیبانی فنی'},
        ],
        'faq': [
            {'q': 'گارانتی چند ماهه است؟', 'a': 'بسته به محصول؛ در صفحه هر کالا مدت گارانتی درج شده است.'},
            {'q': 'امکان تست قبل از خرید هست؟', 'a': 'برای برخی لوازم جانبی بله؛ با پشتیبانی هماهنگ کنید.'},
        ],
        'testimonials': [
            {'name': 'امیر', 'text': 'گوشی اصل بود و سریع رسید.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۱۰ تا ۲۰ — جمعه تعطیل',
    },
    'digital': {
        'announcement': '⚡ تحویل فوری فایل پس از پرداخت',
        'countdown_title': 'تخفیف بسته آموزشی',
        'carousel_source': 'featured',
        'carousel_title': 'پرفروش‌ترین دوره‌ها',
        'trust': [
            {'icon': '⚡', 'label': 'تحویل آنی'},
            {'icon': '📚', 'label': 'محتوای به‌روز'},
            {'icon': '💬', 'label': 'پشتیبانی'},
            {'icon': '🔒', 'label': 'پرداخت امن'},
        ],
        'faq': [
            {'q': 'چطور فایل را دریافت می‌کنم؟', 'a': 'بلافاصله پس از پرداخت موفق، لینک دانلود در ربات و مینی‌اپ فعال می‌شود.'},
            {'q': 'آپدیت رایگان دارید؟', 'a': 'بله، نسخه‌های به‌روز محصولات دیجیتال برای خریداران رایگان است.'},
        ],
        'testimonials': [
            {'name': 'پارسا', 'text': 'دوره کامل و کاربردی بود.', 'rating': 5},
        ],
        'hours': 'پشتیبانی آنلاین ۹ تا ۲۱',
    },
    'pet': {
        'announcement': '🐾 ارسال رایگان خرید بالای ۲ میلیون تومان',
        'countdown_title': 'حراج لوازم حیوانات',
        'carousel_source': 'featured',
        'carousel_title': 'محبوب پت‌لاورها',
        'trust': [
            {'icon': '🐕', 'label': 'برند معتبر'},
            {'icon': '📦', 'label': 'بسته‌بندی بهداشتی'},
            {'icon': '🚚', 'label': 'ارسال سریع'},
            {'icon': '💬', 'label': 'مشاوره تغذیه'},
        ],
        'faq': [
            {'q': 'غذای حیوانات تاریخ دار هست؟', 'a': 'همه محصولات با تاریخ انقضای معتبر و از توزیع‌کنندگان رسمی تهیه می‌شوند.'},
        ],
        'testimonials': [
            {'name': 'نگین', 'text': 'غذای سگم خیلی خوشش اومد.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۱۰ تا ۱۹',
    },
    'general': {
        'announcement': '🎉 خوش آمدید — ارسال سریع به سراسر کشور',
        'countdown_title': 'فروش ویژه',
        'carousel_source': 'featured',
        'carousel_title': 'محصولات ویژه',
        'trust': [
            {'icon': '✅', 'label': 'کیفیت تضمینی'},
            {'icon': '🚚', 'label': 'ارسال سریع'},
            {'icon': '🔄', 'label': 'مرجوعی آسان'},
            {'icon': '💬', 'label': 'پشتیبانی'},
        ],
        'faq': [
            {'q': 'هزینه ارسال چقدره؟', 'a': 'بسته به شهر و وزن مرسوله محاسبه می‌شود.'},
            {'q': 'چطور سفارش بدم؟', 'a': 'از مینی‌اپ محصول را به سبد اضافه کنید و تسویه را تکمیل کنید.'},
        ],
        'testimonials': [
            {'name': 'مشتری', 'text': 'خرید راحت و ارسال به‌موقع بود.', 'rating': 5},
        ],
        'hours': 'شنبه تا پنجشنبه ۹ تا ۲۱',
    },
}

# نگاشت slug الگو → کلید صنف برای کپی
_SLUG_INDUSTRY_GROUP: dict[str, str] = {
    'women-clothing': 'clothing',
    'men-clothing': 'clothing',
    'baby-kids': 'clothing',
    'bags-shoes': 'clothing',
    'jewelry': 'clothing',
    'sports': 'clothing',
    'toys': 'clothing',
    'handicraft': 'clothing',
    'homemade-food': 'food',
    'bakery': 'food',
    'coffee': 'food',
    'nuts': 'food',
    'restaurant': 'food',
    'organic': 'food',
    'cosmetics': 'beauty',
    'perfume': 'beauty',
    'salon': 'beauty',
    'plants': 'home',
    'home-decor': 'home',
    'mobile-acc': 'tech',
    'books': 'general',
    'education': 'digital',
    'digital-products': 'digital',
    'petshop': 'pet',
}


def _block_id(slug: str, key: str) -> str:
    digest = hashlib.md5(f'{slug}:{key}'.encode()).hexdigest()[:8]
    return f'b_{digest}'


def _story_items(categories: list[dict], limit: int = 5) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for cat in categories[:limit]:
        if not isinstance(cat, dict):
            continue
        cslug = (cat.get('slug') or '').strip()
        if not cslug:
            continue
        items.append({
            'title': (cat.get('name') or cslug)[:64],
            'image': '',
            'target': {'kind': 'category', 'value': cslug},
        })
    return items or [{'title': 'جدید', 'image': '', 'target': {'kind': 'category', 'value': ''}}]


def _banner_items(categories: list[dict], limit: int = 4) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for cat in categories[:limit]:
        if not isinstance(cat, dict):
            continue
        cslug = (cat.get('slug') or '').strip()
        if not cslug:
            continue
        items.append({
            'image': '',
            'target': {'kind': 'category', 'value': cslug},
        })
    return items or [{'image': '', 'target': {'kind': 'category', 'value': ''}}]


def _coupon_from_marketing(marketing: dict[str, Any] | None) -> dict[str, Any]:
    welcome = (marketing or {}).get('welcome_discount') or {}
    code = (welcome.get('code') or 'WELCOME10').strip().upper()[:40]
    kind = (welcome.get('kind') or 'percent').strip().lower()
    value = int(welcome.get('value') or 10)
    subtitle = f'{value}٪ تخفیف اولین خرید' if kind == 'percent' else f'{value:,} تومان تخفیف'
    return {
        'title': 'کد تخفیف اولین خرید',
        'code': code,
        'subtitle': subtitle,
        'copy_label': 'کپی کد',
    }


def _ends_at_iso(days: int = 14) -> str:
    return (timezone.now() + timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')


def build_home_blocks_for_template(
    *,
    slug: str,
    industry: str,
    categories: list[dict] | None = None,
    marketing: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """چیدمان صفحهٔ اصلی متناسب با صنف الگو."""
    categories = categories or []
    settings = settings or {}
    group = _SLUG_INDUSTRY_GROUP.get(slug) or industry or 'general'
    if group not in _INDUSTRY_COPY:
        group = 'general'
    copy = _INDUSTRY_COPY[group]

    theme = settings.get('theme') or {}
    accent = theme.get('accent') or theme.get('accent_color') or '#c2402f'
    hero_subtitle = (settings.get('hero_subtitle') or '').strip()
    about = hero_subtitle or (settings.get('hero_title') or 'به فروشگاه ما خوش آمدید')

    first_cat = ''
    if categories and isinstance(categories[0], dict):
        first_cat = (categories[0].get('slug') or '').strip()

    coupon = _coupon_from_marketing(marketing)

    blocks: list[dict[str, Any]] = [
        {
            'id': _block_id(slug, 'announce'),
            'type': 'announcement_bar',
            'text': copy['announcement'],
            'bg': '#111111',
            'color': '#ffffff',
            'dismissible': True,
        },
        {
            'id': _block_id(slug, 'hero'),
            'type': 'hero',
            'variant': 'banner',
        },
        {
            'id': _block_id(slug, 'story'),
            'type': 'story_bar',
            'items': _story_items(categories),
        },
        {
            'id': _block_id(slug, 'search'),
            'type': 'search',
            'placeholder': 'جستجو در محصولات…',
        },
        {
            'id': _block_id(slug, 'coupon'),
            'type': 'coupon',
            **coupon,
        },
        {
            'id': _block_id(slug, 'countdown'),
            'type': 'countdown',
            'title': copy['countdown_title'],
            'ends_at': _ends_at_iso(14),
            'cta_label': 'مشاهده حراج',
            'cta_target': {'kind': 'category', 'value': first_cat} if first_cat else {'kind': 'home', 'value': ''},
            'accent': accent,
        },
        {
            'id': _block_id(slug, 'cats'),
            'type': 'categories',
            'title': 'دسته‌بندی‌ها',
            'columns': 2,
            'limit': 8,
        },
        {
            'id': _block_id(slug, 'carousel'),
            'type': 'product_carousel',
            'title': copy['carousel_title'],
            'source': copy['carousel_source'],
            'limit': 8,
        },
        {
            'id': _block_id(slug, 'banners'),
            'type': 'banner_grid',
            'columns': 2,
            'items': _banner_items(categories, 4),
        },
        {
            'id': _block_id(slug, 'featured'),
            'type': 'featured',
            'title': 'منتخب فروشگاه',
            'limit': 6,
            'layout': 'scroll',
        },
        {
            'id': _block_id(slug, 'testimonials'),
            'type': 'testimonials',
            'title': 'نظر مشتری‌ها',
            'items': copy['testimonials'],
        },
        {
            'id': _block_id(slug, 'trust'),
            'type': 'trust_badges',
            'items': copy['trust'],
        },
        {
            'id': _block_id(slug, 'faq'),
            'type': 'faq',
            'title': 'سوالات متداول',
            'items': copy['faq'],
        },
        {
            'id': _block_id(slug, 'info'),
            'type': 'info',
            'about': about,
            'phones': [],
            'address': 'آدرس فروشگاه را در پنل تنظیمات وارد کنید.',
            'hours': copy['hours'],
            'socials': {'instagram': '', 'telegram': ''},
        },
        {
            'id': _block_id(slug, 'products'),
            'type': 'products',
            'title': 'همه محصولات',
            'layout': theme.get('layout') or 'grid',
            'limit': 0,
        },
    ]

    # صنف دیجیتال: بدون بنر فیزیکی ارسال — ساده‌تر
    if group == 'digital':
        blocks = [b for b in blocks if b['type'] not in ('banner_grid', 'countdown')]
        blocks.insert(4, {
            'id': _block_id(slug, 'richtext'),
            'type': 'rich_text',
            'title': '',
            'html': '<p>پس از پرداخت، <b>فوری</b> به محتوای دوره یا فایل دسترسی دارید.</p>',
            'align': 'right',
        })

    return sanitize_home_blocks(blocks)
