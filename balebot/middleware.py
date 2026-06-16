"""میان‌افزارهای اختصاصی پروژه."""

from django.conf import settings


class MiniAppFrameMiddleware:
    """اجازه نمایش مینی‌اپ داخل iframe بله/تلگرام (مطابق مستندات بله)."""

    CSP = (
        "frame-ancestors 'self' https://*.bale.ai https://web.bale.ai https://*.telegram.org;"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        media_prefix = settings.MEDIA_URL or '/media/'
        if not media_prefix.startswith('/'):
            media_prefix = f'/{media_prefix}'
        if request.path.startswith(media_prefix):
            response['Access-Control-Allow-Origin'] = '*'
            response['Cross-Origin-Resource-Policy'] = 'cross-origin'
            return response
        if not request.path.startswith('/shop/'):
            return response
        response['Content-Security-Policy'] = self.CSP
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response
