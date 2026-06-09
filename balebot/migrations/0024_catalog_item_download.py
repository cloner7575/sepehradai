from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0023_alter_catalogitemmedia_item_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogitem',
            name='cover',
            field=models.ImageField(
                blank=True,
                help_text='تصویر کاور برای نمایش (مخصوص فایل دانلود)',
                null=True,
                upload_to='catalog/items/covers/%Y/%m/',
            ),
        ),
        migrations.AddField(
            model_name='catalogitem',
            name='download_file',
            field=models.FileField(
                blank=True,
                help_text='فایل اصلی قابل دانلود',
                null=True,
                upload_to='catalog/items/downloads/%Y/%m/',
            ),
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='item_type',
            field=models.CharField(
                choices=[
                    ('product', 'محصول'),
                    ('portfolio', 'نمونه‌کار'),
                    ('service', 'خدمت'),
                    ('digital', 'دیجیتال'),
                    ('download', 'فایل دانلود'),
                ],
                default='product',
                max_length=16,
            ),
        ),
    ]
