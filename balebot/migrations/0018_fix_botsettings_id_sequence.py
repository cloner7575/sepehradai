# Reset PostgreSQL sequence after BotSettings PK changed from fixed ids to BigAutoField.

from django.db import migrations


def reset_botsettings_id_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('balebot_botsettings', 'id'),
                COALESCE((SELECT MAX(id) FROM balebot_botsettings), 1),
                true
            )
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0017_alter_botsettings_id'),
    ]

    operations = [
        migrations.RunPython(reset_botsettings_id_sequence, migrations.RunPython.noop),
    ]
