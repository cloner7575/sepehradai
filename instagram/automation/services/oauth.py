from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core import signing
from django.utils import timezone

from instagram.automation.models import InstagramConnection, InstagramAuditLog
from instagram.automation.services.meta_client import MetaGraphClient, MetaAPIError
from instagram.automation.services.token_crypto import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)

OAUTH_STATE_SALT = 'instagram-meta-oauth'
OAUTH_STATE_MAX_AGE = 600

# مجوزهای پایه — برخی نیازمند App Review هستند
DEFAULT_SCOPES = [
    'instagram_business_basic',
    'instagram_business_manage_messages',
    'instagram_business_manage_comments',
]
WEBHOOK_FIELDS = [
    'messages',
    'messaging_postbacks',
    'messaging_seen',
    'messaging_referral',
    'message_reactions',
    'comments',
    'live_comments',
    'mentions',
]



def build_oauth_state(*, workspace_id: int, user_id: int) -> str:
    return signing.dumps(
        {
            'workspace_id': workspace_id,
            'user_id': user_id,
            'nonce': secrets.token_urlsafe(16),
            'ts': int(time.time()),
        },
        salt=OAUTH_STATE_SALT,
    )


def parse_oauth_state(state: str) -> dict[str, Any]:
    return signing.loads(state, salt=OAUTH_STATE_SALT, max_age=OAUTH_STATE_MAX_AGE)


def get_oauth_authorize_url(*, workspace_id: int, user_id: int) -> str:
    app_id = getattr(settings, 'INSTAGRAM_APP_ID', '') or ''
    redirect = getattr(settings, 'INSTAGRAM_REDIRECT_URI', '') or ''
    if not app_id or not redirect:
        raise ValueError('Instagram OAuth settings are incomplete')
    state = build_oauth_state(workspace_id=workspace_id, user_id=user_id)
    params = {
        'client_id': app_id,
        'redirect_uri': redirect,
        'state': state,
        'scope': ','.join(DEFAULT_SCOPES),
        'response_type': 'code',
        'enable_fb_login': '0',
        'force_authentication': '1',
    }
    return f'https://www.instagram.com/oauth/authorize?{urlencode(params)}'


def exchange_code_for_token(code: str) -> dict[str, Any]:
    resp = requests.post(
        'https://api.instagram.com/oauth/access_token',
        data={
            'client_id': settings.INSTAGRAM_APP_ID,
            'client_secret': settings.INSTAGRAM_APP_SECRET,
            'redirect_uri': settings.INSTAGRAM_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'code': code,
        },
        timeout=20,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or 'access_token' not in data:
        logger.warning('OAuth token exchange failed status=%s', resp.status_code)
        raise MetaAPIError(
            category=__import__(
                'instagram.automation.services.meta_client', fromlist=['MetaErrorCategory']
            ).MetaErrorCategory.AUTHENTICATION,
            internal_code='META_OAUTH_EXCHANGE',
            message_fa='تبادل کد OAuth با Meta ناموفق بود.',
            http_status=resp.status_code,
        )
    return data


def exchange_long_lived_token(short_token: str) -> dict[str, Any]:
    resp = requests.get(
        'https://graph.instagram.com/access_token',
        params={
            'grant_type': 'ig_exchange_token',
            'client_secret': settings.INSTAGRAM_APP_SECRET,
            'access_token': short_token,
        },
        timeout=20,
    )
    data = resp.json() if resp.content else {}
    if 'access_token' not in data:
        raise MetaAPIError(
            category=__import__(
                'instagram.automation.services.meta_client', fromlist=['MetaErrorCategory']
            ).MetaErrorCategory.AUTHENTICATION,
            internal_code='META_OAUTH_LONGLIVE',
            message_fa='تمدید توکن بلندمدت ناموفق بود.',
            http_status=resp.status_code,
        )
    return data


def refresh_long_lived_token(access_token: str) -> dict[str, Any]:
    resp = requests.get(
        'https://graph.instagram.com/refresh_access_token',
        params={
            'grant_type': 'ig_refresh_token',
            'access_token': access_token,
        },
        timeout=20,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or 'access_token' not in data:
        raise MetaAPIError(
            category=__import__(
                'instagram.automation.services.meta_client', fromlist=['MetaErrorCategory']
            ).MetaErrorCategory.AUTHENTICATION,
            internal_code='META_OAUTH_REFRESH',
            message_fa='Instagram token refresh failed.',
            http_status=resp.status_code,
        )
    return data


def get_direct_instagram_profile(access_token: str, fallback_user_id: str = '') -> dict[str, Any]:
    client = MetaGraphClient(
        access_token=access_token,
        host='graph.instagram.com',
    )
    data = client.get(
        'me',
        params={'fields': 'user_id,username,name,profile_picture_url'},
    )
    ig_id = str(data.get('user_id') or data.get('id') or fallback_user_id or '')
    if not ig_id:
        raise MetaAPIError(
            category=__import__(
                'instagram.automation.services.meta_client', fromlist=['MetaErrorCategory']
            ).MetaErrorCategory.VALIDATION,
            internal_code='META_PROFILE_NO_ID',
            message_fa='Instagram account profile could not be loaded.',
        )
    return {
        'instagram_account_id': ig_id,
        'page_id': '',
        'page_name': '',
        'page_access_token': access_token,
        'username': data.get('username') or '',
        'profile_name': data.get('name') or '',
        'profile_picture_url': data.get('profile_picture_url') or '',
    }


def list_connectable_pages(user_token: str) -> list[dict[str, Any]]:
    client = MetaGraphClient(access_token=user_token)
    data = client.get(
        'me/accounts',
        params={'fields': 'id,name,access_token,instagram_business_account{id,username,name,profile_picture_url}'},
    )
    pages = []
    for page in data.get('data') or []:
        ig = page.get('instagram_business_account') or {}
        if not ig.get('id'):
            continue
        pages.append(
            {
                'page_id': page.get('id'),
                'page_name': page.get('name'),
                'page_access_token': page.get('access_token'),
                'instagram_account_id': ig.get('id'),
                'username': ig.get('username') or '',
                'profile_name': ig.get('name') or '',
                'profile_picture_url': ig.get('profile_picture_url') or '',
            }
        )
    return pages


def connect_instagram_account(
    *,
    workspace,
    user,
    page: dict[str, Any],
    scopes: list[str] | None = None,
    auth_provider: str = InstagramConnection.AuthProvider.FACEBOOK_LEGACY,
    token_data: dict[str, Any] | None = None,
) -> InstagramConnection:
    ig_id = page['instagram_account_id']
    existing = (
        InstagramConnection.objects.filter(
            instagram_account_id=ig_id,
            connection_status=InstagramConnection.ConnectionStatus.CONNECTED,
        )
        .exclude(workspace_id=workspace.id)
        .first()
    )
    if existing:
        raise ValueError('این حساب اینستاگرام به فضای کاری دیگری متصل است.')

    token = page.get('page_access_token') or ''
    expires = None
    token_data = token_data or {}
    expires_in = int(token_data.get('expires_in') or 0)
    if expires_in:
        expires = timezone.now() + timedelta(seconds=expires_in)

    conn, _ = InstagramConnection.objects.update_or_create(
        workspace=workspace,
        instagram_account_id=ig_id,
        defaults={
            'connected_by': user,
            'auth_provider': auth_provider,
            'facebook_page_id': page.get('page_id') or '',
            'username': page.get('username') or '',
            'profile_name': page.get('profile_name') or '',
            'profile_picture_url': page.get('profile_picture_url') or '',
            'encrypted_access_token': encrypt_token(token),
            'token_expires_at': expires,
            'scopes': scopes or DEFAULT_SCOPES,
            'token_last_refreshed_at': timezone.now(),
            'webhook_subscribed_fields': [],
            'capability_status': {},
            'connection_status': InstagramConnection.ConnectionStatus.CONNECTED,
            'webhook_status': InstagramConnection.WebhookStatus.UNKNOWN,
            'last_sync_at': timezone.now(),
            'last_error_code': '',
            'last_error_message_sanitized': '',
            'disconnected_at': None,
        },
    )
    InstagramAuditLog.objects.create(
        workspace=workspace,
        actor_type=InstagramAuditLog.ActorType.USER,
        actor_id=str(user.id),
        action='instagram.connect',
        entity_type='InstagramConnection',
        entity_id=str(conn.id),
        after_data_redacted={
            'instagram_account_id': ig_id,
            'username': conn.username,
        },
    )
    return conn


def subscribe_connection_webhooks(conn: InstagramConnection) -> dict[str, Any]:
    client = client_for_connection(conn)
    result = client.subscribe_webhooks(conn.instagram_account_id, WEBHOOK_FIELDS)
    granted = set(conn.scopes or [])
    capabilities = {
        'messaging': 'instagram_business_manage_messages' in granted,
        'comments': 'instagram_business_manage_comments' in granted,
        'private_reply': 'instagram_business_manage_comments' in granted,
    }
    from instagram.automation.models import WorkspaceInstagramEntitlement

    entitlement, _ = WorkspaceInstagramEntitlement.objects.get_or_create(workspace=conn.workspace)
    entitlement.meta_messaging_approved = capabilities['messaging']
    entitlement.meta_comments_approved = capabilities['comments']
    entitlement.meta_private_reply_approved = capabilities['private_reply']
    entitlement.save(update_fields=[
        'meta_messaging_approved',
        'meta_comments_approved',
        'meta_private_reply_approved',
        'updated_at',
    ])
    conn.webhook_subscribed_fields = list(WEBHOOK_FIELDS)
    conn.capability_status = capabilities
    conn.webhook_status = InstagramConnection.WebhookStatus.ACTIVE
    conn.last_error_code = ''
    conn.last_error_message_sanitized = ''
    conn.save(
        update_fields=[
            'webhook_subscribed_fields',
            'capability_status',
            'webhook_status',
            'last_error_code',
            'last_error_message_sanitized',
            'updated_at',
        ]
    )
    return result


def disconnect_connection(conn: InstagramConnection, *, user=None) -> None:
    conn.encrypted_access_token = ''
    conn.connection_status = InstagramConnection.ConnectionStatus.DISCONNECTED
    conn.disconnected_at = timezone.now()
    conn.save(
        update_fields=[
            'encrypted_access_token',
            'connection_status',
            'disconnected_at',
            'updated_at',
        ]
    )
    InstagramAuditLog.objects.create(
        workspace_id=conn.workspace_id,
        actor_type=InstagramAuditLog.ActorType.USER if user else InstagramAuditLog.ActorType.SYSTEM,
        actor_id=str(user.id) if user else '',
        action='instagram.disconnect',
        entity_type='InstagramConnection',
        entity_id=str(conn.id),
    )


def client_for_connection(conn: InstagramConnection) -> MetaGraphClient:
    token = decrypt_token(conn.encrypted_access_token)
    if not token:
        raise MetaAPIError(
            category=__import__(
                'instagram.automation.services.meta_client', fromlist=['MetaErrorCategory']
            ).MetaErrorCategory.DISCONNECTED,
            internal_code='META_NO_TOKEN',
            message_fa='توکن اتصال موجود نیست. حساب را دوباره متصل کنید.',
        )
    host = (
        'graph.instagram.com'
        if conn.auth_provider == InstagramConnection.AuthProvider.INSTAGRAM_LOGIN
        else 'graph.facebook.com'
    )
    return MetaGraphClient(access_token=token, host=host)


def test_connection(conn: InstagramConnection) -> dict[str, Any]:
    client = client_for_connection(conn)
    data = client.get_ig_user(conn.instagram_account_id)
    conn.last_sync_at = timezone.now()
    conn.last_error_code = ''
    conn.last_error_message_sanitized = ''
    if data.get('username'):
        conn.username = data['username']
    if data.get('name'):
        conn.profile_name = data['name']
    if data.get('profile_picture_url'):
        conn.profile_picture_url = data['profile_picture_url']
    conn.save()
    return {
        'ok': True,
        'username': conn.username,
        'instagram_account_id': conn.instagram_account_id,
    }


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    configured = getattr(settings, 'INSTAGRAM_APP_SECRET', '') or getattr(settings, 'META_APP_SECRET', '')
    secret = configured.encode('utf-8')
    if not secret or not signature_header:
        return False
    if signature_header.startswith('sha256='):
        their = signature_header[7:]
    else:
        their = signature_header
    digest = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, their)
