from django.db import migrations


def forwards(apps, schema_editor):
    BotSettings = apps.get_model('balebot', 'BotSettings')
    settings = BotSettings.objects.filter(pk=1).first()
    if not settings:
        return
    flow = getattr(settings, 'start_flow', None) or {}
    if isinstance(flow, dict) and flow.get('version') == 2:
        items = (flow.get('root') or {}).get('items') or []
        if items:
            return
    from balebot.services.flow_sanitize import migrate_inline_keyboard_to_flow

    old_kb = getattr(settings, 'start_inline_keyboard', None)
    settings.start_flow = migrate_inline_keyboard_to_flow(old_kb)
    settings.save(update_fields=['start_flow'])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0012_start_flow_and_flow_media'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
