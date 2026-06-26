from django.templatetags.static import static

from core.brand import BRAND_PURPLE, BRAND_TEAL

DEFAULT_ICON = 'balebot/brand/icon.svg'
DEFAULT_LOGO = 'balebot/brand/logo.svg'
DEFAULT_FAVICON = 'balebot/brand/icon.svg'


def _static_url(path: str) -> str:
    return static(path)


def _file_url(field) -> str:
    if field and getattr(field, 'name', ''):
        try:
            return field.url
        except (ValueError, AttributeError):
            return ''
    return ''


def get_brand_context(settings_obj=None) -> dict:
    if settings_obj is None:
        from landing.models import LandingSettings
        settings_obj = LandingSettings.get_solo()

    icon_url = _file_url(getattr(settings_obj, 'brand_icon_svg', None)) or _static_url(DEFAULT_ICON)
    logo_url = _file_url(getattr(settings_obj, 'brand_logo_svg', None)) or ''
    favicon_url = _file_url(getattr(settings_obj, 'brand_favicon_svg', None)) or _static_url(DEFAULT_FAVICON)

    wordmark_primary = (getattr(settings_obj, 'brand_wordmark_primary', '') or 'Rahat').strip() or 'Rahat'
    wordmark_accent = (getattr(settings_obj, 'brand_wordmark_accent', '') or 'sell').strip() or 'sell'

    return {
        'brand_icon_url': icon_url,
        'brand_logo_url': logo_url,
        'brand_favicon_url': favicon_url,
        'brand_wordmark_primary': wordmark_primary,
        'brand_wordmark_accent': wordmark_accent,
        'brand_use_full_logo': bool(logo_url),
        'brand_purple': BRAND_PURPLE,
        'brand_teal': BRAND_TEAL,
    }


def get_brand_context_fallback() -> dict:
    return {
        'brand_icon_url': _static_url(DEFAULT_ICON),
        'brand_logo_url': '',
        'brand_favicon_url': _static_url(DEFAULT_FAVICON),
        'brand_wordmark_primary': 'Rahat',
        'brand_wordmark_accent': 'sell',
        'brand_use_full_logo': False,
        'brand_purple': BRAND_PURPLE,
        'brand_teal': BRAND_TEAL,
    }
