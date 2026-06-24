from django.db import migrations, models


def migrate_portfolio_to_showcase(apps, schema_editor):
    CatalogItem = apps.get_model('balebot', 'CatalogItem')
    CatalogItem.objects.filter(item_type='portfolio').update(item_type='showcase')


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0031_catalog_checkout_form'),
    ]

    operations = [
        migrations.RunPython(migrate_portfolio_to_showcase, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='catalogitem',
            name='item_type',
            field=models.CharField(
                choices=[
                    ('product', 'محصول'),
                    ('download', 'فایل دانلود'),
                    ('video', 'ویدیو و آموزش'),
                    ('service', 'خدمت'),
                    ('showcase', 'معرفی و نمونه\u200cکار'),
                ],
                default='product',
                max_length=16,
            ),
        ),
    ]
