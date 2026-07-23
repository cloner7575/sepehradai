from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils.crypto import salted_hmac
from django.utils import timezone

from instagram.automation.models import InstagramTrackedLink


DEFAULT_ALLOWED_HOSTS = (
    'localhost',
    '127.0.0.1',
)


def allowed_redirect_hosts() -> set[str]:
    hosts = set(DEFAULT_ALLOWED_HOSTS)
    for h in getattr(settings, 'ALLOWED_HOSTS', []) or []:
        if h and h != '*':
            hosts.add(h.lower())
    extra = getattr(settings, 'INSTAGRAM_LINK_ALLOWLIST', '') or ''
    for h in extra.split(','):
        h = h.strip().lower()
        if h:
            hosts.add(h)
    return hosts


def is_url_allowed(url: str) -> bool:
    if _is_relative_ok(url):
        return True
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ('http', 'https'):
        return False
    host = (parsed.hostname or '').lower()
    if not host:
        return False
    if host.startswith('10.') or host.startswith('192.168.') or host.startswith('169.254.'):
        return False
    return host in allowed_redirect_hosts()


def _is_relative_ok(url: str) -> bool:
    return url.startswith('/') and not url.startswith('//')


def create_tracked_link(
    *,
    workspace,
    target_url: str,
    flow=None,
    rule=None,
    contact=None,
    product_id=None,
    source_media_id=None,
    campaign_id: str = '',
) -> InstagramTrackedLink:
    if not is_url_allowed(target_url) and not _is_relative_ok(target_url):
        raise ValueError('آدرس مقصد در allowlist نیست.')
    code = secrets.token_urlsafe(12)[:16]
    storefront = getattr(workspace, 'instagram_storefront', None)
    hours = int(getattr(storefront, 'secure_link_hours', 24) or 24)
    return InstagramTrackedLink.objects.create(
        workspace=workspace,
        short_code=code,
        code_digest=hashlib.sha256(code.encode('utf-8')).hexdigest(),
        target_url=target_url,
        flow=flow,
        rule=rule,
        contact=contact,
        product_id=product_id,
        source_media_id=source_media_id,
        campaign_id=campaign_id or '',
        expires_at=timezone.now() + timedelta(hours=max(1, min(hours, 168))),
    )


def _session_digest(session_key: str, link_id: int) -> str:
    return salted_hmac('instagram.checkout.session', f'{session_key}:{link_id}').hexdigest()


@transaction.atomic
def claim_tracked_link(short_code: str, request) -> tuple[InstagramTrackedLink, str] | None:
    digest = hashlib.sha256(short_code.encode('utf-8')).hexdigest()
    link = (
        InstagramTrackedLink.objects.select_for_update()
        .select_related('workspace')
        .filter(code_digest=digest, short_code=short_code)
        .first()
    )
    now = timezone.now()
    if not link or link.revoked_at or (link.expires_at and link.expires_at <= now):
        return None
    if not is_url_allowed(link.target_url) and not _is_relative_ok(link.target_url):
        return None
    if not request.session.session_key:
        request.session.create()
    session_hash = _session_digest(request.session.session_key, link.pk)
    if link.claimed_session_hash and not secrets.compare_digest(link.claimed_session_hash, session_hash):
        return None
    if not link.claimed_session_hash:
        link.claimed_session_hash = session_hash
        link.claimed_at = now
    link.click_count += 1
    link.last_clicked_at = now
    link.save(update_fields=['claimed_session_hash', 'claimed_at', 'click_count', 'last_clicked_at'])
    request.session['instagram_checkout_session'] = {
        'link_id': link.pk,
        'workspace_id': link.workspace_id,
        'session_hash': session_hash,
    }
    ttl = max(60, int((link.expires_at - now).total_seconds())) if link.expires_at else 86400
    request.session.set_expiry(ttl)
    return link, link.target_url


def resolve_and_track_click(short_code: str) -> str | None:
    # Retained for backwards compatibility with internal callers.
    link = InstagramTrackedLink.objects.filter(short_code=short_code).first()
    now = timezone.now()
    if not link or link.revoked_at or (link.expires_at and link.expires_at <= now):
        return None
    return link.target_url if is_url_allowed(link.target_url) else None
