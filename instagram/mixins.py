from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from balebot.platform import require_instagram_access_for_request
from balebot.views_panel import PanelAccessMixin, WorkspaceScopedMixin


class InstagramPanelMixin(WorkspaceScopedMixin, PanelAccessMixin):
    """دسترسی پنل + workspace + پرچم allow_instagram روی workspace."""

    def dispatch(self, request, *args, **kwargs):
        try:
            require_instagram_access_for_request(request)
        except PermissionDenied:
            messages.error(request, 'دسترسی بخش اینستاگرام برای این پنل فعال نیست.')
            return redirect('panel_dashboard')
        return super().dispatch(request, *args, **kwargs)
