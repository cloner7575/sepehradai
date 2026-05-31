# Fix BotSettings rows that require explicit primary keys (1=bale, 2=telegram)

from django.db import migrations, models


def ensure_botsettings_rows(apps, schema_editor):
    BotSettings = apps.get_model('balebot', 'BotSettings')

    if not BotSettings.objects.filter(pk=1).exists():
        BotSettings.objects.create(
            id=1,
            platform='bale',
            panel_brand_title='کنترل بازو',
            panel_brand_subtitle='مدیریت کمپین و مخاطبان',
        )
    else:
        bale = BotSettings.objects.get(pk=1)
        if bale.platform != 'bale':
            bale.platform = 'bale'
            bale.save(update_fields=['platform'])

    if not BotSettings.objects.filter(pk=2).exists():
        BotSettings.objects.create(
            id=2,
            platform='telegram',
            panel_brand_title='کنترل تلگرام',
            panel_brand_subtitle='مدیریت کمپین و مخاطبان',
        )
    else:
        telegram = BotSettings.objects.get(pk=2)
        if telegram.platform != 'telegram':
            telegram.platform = 'telegram'
            telegram.save(update_fields=['platform'])


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0014_multi_platform'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botsettings',
            name='id',
            field=models.PositiveSmallIntegerField(editable=False, primary_key=True, serialize=False),
        ),
        migrations.RunPython(ensure_botsettings_rows, migrations.RunPython.noop),
    ]
