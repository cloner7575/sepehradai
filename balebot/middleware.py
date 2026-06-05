"""میان‌افزارهای اختصاصی پروژه."""


class MiniAppFrameMiddleware:
    """اجازه نمایش مینی‌اپ داخل iframe بله/تلگرام (مطابق مستندات بله)."""

    CSP = (
        "frame-ancestors 'self' https://*.bale.ai https://web.bale.ai https://*.telegram.org;"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith('/shop/'):
            return response
        response['Content-Security-Policy'] = self.CSP
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response
