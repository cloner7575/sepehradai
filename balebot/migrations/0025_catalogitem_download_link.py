from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0024_catalog_item_download'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogitem',
            name='download_link',
            field=models.URLField(
                blank=True,
                default='',
                help_text='لینک مستقیم دانلود (گوگل\u200cدرایو، دراپ\u200cباکس و...)',
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='download_file',
            field=models.FileField(
                blank=True,
                help_text='فایل اصلی قابل دانلود (آپلود روی سرور)',
                null=True,
                upload_to='catalog/items/downloads/%Y/%m/',
            ),
        ),
    ]
