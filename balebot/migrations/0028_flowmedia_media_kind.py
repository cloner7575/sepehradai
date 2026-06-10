from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0027_subscriber_miniapp_and_catalog_channel'),
    ]

    operations = [
        migrations.AddField(
            model_name='flowmedia',
            name='media_kind',
            field=models.CharField(
                choices=[
                    ('photo', 'عکس'),
                    ('video', 'ویدیو'),
                    ('voice', 'صدا'),
                    ('document', 'سند'),
                ],
                db_index=True,
                default='photo',
                max_length=16,
            ),
        ),
    ]
