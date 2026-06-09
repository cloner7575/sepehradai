from django.db import migrations, models


def migrate_digital_to_product(apps, schema_editor):
    CatalogItem = apps.get_model('balebot', 'CatalogItem')
    CatalogItem.objects.filter(item_type='digital').update(item_type='product')


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0025_catalogitem_download_link'),
    ]

    operations = [
        migrations.RunPython(migrate_digital_to_product, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='catalogitem',
            name='item_type',
            field=models.CharField(
                choices=[
                    ('product', 'محصول'),
                    ('portfolio', 'نمونه\u200cکار'),
                    ('service', 'خدمت'),
                    ('download', 'فایل دانلود'),
                ],
                default='product',
                max_length=16,
            ),
        ),
    ]
