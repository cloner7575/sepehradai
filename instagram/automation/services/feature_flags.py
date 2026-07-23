from __future__ import annotations

from instagram.automation.services.permissions import get_or_create_entitlement


FLAG_FIELDS = (
    'instagram_module',
    'instagram_connection',
    'instagram_inbox',
    'instagram_dm_automation',
    'instagram_comment_automation',
    'instagram_private_reply',
    'instagram_flow_builder',
    'instagram_analytics',
    'instagram_ai_assistant',
)


def feature_enabled(workspace, flag: str) -> bool:
    if not workspace or not getattr(workspace, 'allow_instagram', False):
        return False
    if flag not in FLAG_FIELDS:
        return False
    ent = get_or_create_entitlement(workspace)
    if not ent.instagram_module and flag != 'instagram_module':
        return False
    return bool(getattr(ent, flag, False))


def meta_capability_status(workspace, capability: str) -> str:
    """
    returns: enabled | needs_meta_review | disabled
    """
    ent = get_or_create_entitlement(workspace)
    mapping = {
        'messaging': ('instagram_inbox', 'meta_messaging_approved'),
        'comments': ('instagram_comment_automation', 'meta_comments_approved'),
        'private_reply': ('instagram_private_reply', 'meta_private_reply_approved'),
    }
    if capability not in mapping:
        return 'disabled'
    flag, approved = mapping[capability]
    if not getattr(ent, flag, False):
        return 'disabled'
    if not getattr(ent, approved, False):
        return 'needs_meta_review'
    return 'enabled'
