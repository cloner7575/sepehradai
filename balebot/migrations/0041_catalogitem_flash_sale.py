from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0040_resync_store_templates_home_blocks'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogitem',
            name='is_flash_sale',
            field=models.BooleanField(default=False, help_text='نمایش در بخش حراج مینی‌اپ'),
        ),
        migrations.AddField(
            model_name='catalogitem',
            name='flash_sale_starts_at',
            field=models.DateTimeField(blank=True, help_text='شروع حراج (اختیاری)', null=True),
        ),
        migrations.AddField(
            model_name='catalogitem',
            name='flash_sale_ends_at',
            field=models.DateTimeField(blank=True, help_text='پایان حراج (اختیاری)', null=True),
        ),
    ]
