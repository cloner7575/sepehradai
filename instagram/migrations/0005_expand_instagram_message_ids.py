from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('instagram', '0004_tracked_link_source_media'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instagramwebhookevent',
            name='external_event_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=512),
        ),
        migrations.AlterField(
            model_name='instagrammessage',
            name='external_message_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=512),
        ),
        migrations.AlterField(
            model_name='instagrammessage',
            name='reply_to_external_message_id',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
    ]
