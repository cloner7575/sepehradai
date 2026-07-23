from __future__ import annotations

INSTAGRAM_PERMISSIONS = (
    'instagram.view',
    'instagram.connect',
    'instagram.disconnect',
    'instagram.inbox.view',
    'instagram.inbox.reply',
    'instagram.inbox.assign',
    'instagram.automation.view',
    'instagram.automation.create',
    'instagram.automation.edit',
    'instagram.automation.publish',
    'instagram.automation.delete',
    'instagram.analytics.view',
    'instagram.settings.manage',
    'instagram.logs.view',
    'instagram.events.replay',
    'instagram.export',
)

# نقش‌های مفهومی — map به دسترسی‌های پیش‌فرض
ROLE_PERMISSIONS = {
    'owner': list(INSTAGRAM_PERMISSIONS),
    'admin': list(INSTAGRAM_PERMISSIONS),
    'manager': [
        'instagram.view',
        'instagram.inbox.view',
        'instagram.inbox.reply',
        'instagram.inbox.assign',
        'instagram.automation.view',
        'instagram.automation.create',
        'instagram.automation.edit',
        'instagram.automation.publish',
        'instagram.analytics.view',
        'instagram.settings.manage',
        'instagram.logs.view',
        'instagram.export',
    ],
    'support_agent': [
        'instagram.view',
        'instagram.inbox.view',
        'instagram.inbox.reply',
        'instagram.automation.view',
        'instagram.analytics.view',
    ],
    'viewer': [
        'instagram.view',
        'instagram.inbox.view',
        'instagram.automation.view',
        'instagram.analytics.view',
    ],
}


def get_or_create_entitlement(workspace):
    from instagram.automation.models import WorkspaceInstagramEntitlement

    ent, _ = WorkspaceInstagramEntitlement.objects.get_or_create(workspace=workspace)
    return ent


def user_has_instagram_perm(user, workspace, perm: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if not getattr(workspace, 'allow_instagram', False):
        return False
    if user.is_superuser:
        return True
    if hasattr(workspace, 'owner_id') and workspace.owner_id == user.id:
        return True
    ent = get_or_create_entitlement(workspace)
    staff_map = ent.staff_permissions or {}
    user_perms = staff_map.get(str(user.id)) or staff_map.get(user.username) or []
    if isinstance(user_perms, str):
        # نقش مفهومی
        user_perms = ROLE_PERMISSIONS.get(user_perms, [])
    if perm in user_perms:
        return True
    # staff بدون map سفارشی: دسترسی viewer
    if user.is_staff and perm in ROLE_PERMISSIONS['viewer']:
        return True
    return False
