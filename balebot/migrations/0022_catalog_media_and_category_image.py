from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0021_catalog_payment_methods'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogcategory',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='catalog/categories/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='catalogitemimage',
            name='media_type',
            field=models.CharField(
                choices=[('image', 'تصویر'), ('video', 'ویدیو'), ('file', 'فایل')],
                default='image',
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name='catalogitemimage',
            name='title',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.RenameField(
            model_name='catalogitemimage',
            old_name='image',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='catalogitemimage',
            name='file',
            field=models.FileField(upload_to='catalog/items/%Y/%m/'),
        ),
        migrations.RenameModel(
            old_name='CatalogItemImage',
            new_name='CatalogItemMedia',
        ),
        migrations.AlterModelOptions(
            name='catalogitemmedia',
            options={
                'ordering': ['sort_order', 'id'],
                'verbose_name': 'رسانه آیتم',
                'verbose_name_plural': 'رسانه‌های آیتم',
            },
        ),
    ]
