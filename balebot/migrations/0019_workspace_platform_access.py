from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0018_fix_botsettings_id_sequence'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='allow_bale',
            field=models.BooleanField(default=True, verbose_name='دسترسی بله'),
        ),
        migrations.AddField(
            model_name='workspace',
            name='allow_telegram',
            field=models.BooleanField(default=True, verbose_name='دسترسی تلگرام'),
        ),
    ]
