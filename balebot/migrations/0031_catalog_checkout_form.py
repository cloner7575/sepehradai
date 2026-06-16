from django.db import migrations, models

import balebot.models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0030_catalog_hero_background'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogorder',
            name='customer_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='checkout_form',
            field=models.JSONField(blank=True, default=balebot.models.default_checkout_form),
        ),
    ]
