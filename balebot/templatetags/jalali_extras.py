from django import template

from balebot.services.catalog_currency import format_number as _format_number, format_toman as _format_toman
from balebot.services.jalali_datetime import aware_to_jalali_parts

register = template.Library()


@register.filter(name='jalali_datetime')
def jalali_datetime(value):
    date_part, time_part = aware_to_jalali_parts(value)
    if not date_part:
        return '-'
    return f'{date_part} - {time_part}'


@register.filter(name='get_item')
def get_item(mapping, key):
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter(name='format_toman')
def format_toman(value):
    """مقدار ریال → عدد تومان با جداکننده (مثلاً 385,000)."""
    return _format_toman(value)


@register.filter(name='format_rial')
def format_rial(value):
    """سازگاری با قالب‌های قبلی — همان format_toman."""
    return _format_toman(value)


@register.filter(name='format_number')
def format_number(value):
    """عدد خام با جداکننده هزارگان (بدون تبدیل ریال/تومان)."""
    return _format_number(value)
