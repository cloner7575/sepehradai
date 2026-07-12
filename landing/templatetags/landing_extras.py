from django import template

from landing.services.legal_text import format_legal_text_html

register = template.Library()


@register.filter(name='format_legal_text')
def format_legal_text(value):
    return format_legal_text_html(value)
