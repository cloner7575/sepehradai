from landing.constants import BUSINESS_TYPES as FALLBACK_BUSINESS_TYPES
from landing.models import BusinessCategory


def active_categories_qs():
    return BusinessCategory.objects.filter(is_active=True).order_by('sort_order', 'id')


def form_choices() -> list[tuple[str, str]]:
    categories = list(active_categories_qs())
    if not categories:
        return [('', 'انتخاب صنف')] + list(FALLBACK_BUSINESS_TYPES) + [('سایر', 'سایر')]
    return [('', 'انتخاب صنف')] + [(cat.name, cat.name) for cat in categories]


def landing_chip_names() -> list[str]:
    categories = list(
        BusinessCategory.objects.filter(is_active=True, show_on_landing=True).order_by('sort_order', 'id')
    )
    if not categories:
        return [label for _, label in FALLBACK_BUSINESS_TYPES] + ['سایر']
    return [cat.name for cat in categories]


def other_category_label() -> str:
    cat = BusinessCategory.objects.filter(is_other=True, is_active=True).first()
    if cat:
        return cat.name
    return 'سایر'


def is_other_selection(value: str) -> bool:
    label = (value or '').strip()
    if not label:
        return False
    if label == 'سایر':
        return True
    return BusinessCategory.objects.filter(is_other=True, is_active=True, name=label).exists()
