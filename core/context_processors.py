from django.db.utils import OperationalError

from core.brand import (
    BRAND_PURPLE,
    BRAND_TEAL,
    SITE_DESCRIPTION,
    SITE_NAME_EN,
    SITE_NAME_FA,
    SITE_NAME_FULL,
    SITE_TAGLINE,
)
from landing.services.brand_assets import get_brand_context, get_brand_context_fallback


def site_brand(request):
    ctx = {
        'site_name_fa': SITE_NAME_FA,
        'site_name_en': SITE_NAME_EN,
        'site_name_full': SITE_NAME_FULL,
        'site_tagline': SITE_TAGLINE,
        'site_description': SITE_DESCRIPTION,
        'brand_purple': BRAND_PURPLE,
        'brand_teal': BRAND_TEAL,
    }
    try:
        ctx.update(get_brand_context())
    except OperationalError:
        ctx.update(get_brand_context_fallback())
    except Exception:
        ctx.update(get_brand_context_fallback())
    return ctx
