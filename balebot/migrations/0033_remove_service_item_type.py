from django.db import migrations, models


def migrate_service_items(apps, schema_editor):
    CatalogItem = apps.get_model('balebot', 'CatalogItem')
    for item in CatalogItem.objects.filter(item_type='service'):
        if item.price and item.sale_mode in ('buyable', 'both'):
            item.item_type = 'product'
        else:
            item.item_type = 'showcase'
        item.save(update_fields=['item_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0032_catalog_item_types'),
    ]

    operations = [
        migrations.RunPython(migrate_service_items, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='catalogitem',
            name='item_type',
            field=models.CharField(
                choices=[
                    ('product', 'محصول'),
                    ('download', 'فایل دانلود'),
                    ('video', 'ویدیو و آموزش'),
                    ('showcase', 'معرفی و نمونه\u200cکار'),
                ],
                default='product',
                max_length=16,
            ),
        ),
    ]
