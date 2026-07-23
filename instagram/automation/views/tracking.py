from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.views import View

from instagram.automation.services.link_tracking import claim_tracked_link


class TrackedLinkRedirectView(View):
    def get(self, request, code: str):
        claimed = claim_tracked_link(code, request)
        if not claimed:
            return HttpResponseForbidden('لینک نامعتبر')
        _, url = claimed
        return HttpResponseRedirect(url)
