from django import template

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
