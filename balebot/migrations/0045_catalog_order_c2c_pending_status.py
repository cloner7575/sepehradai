from django.db import migrations, models


def migrate_card_to_card_receipt_orders(apps, schema_editor):
    CatalogOrder = apps.get_model('balebot', 'CatalogOrder')
    CatalogOrder.objects.filter(
        payment_method='card_to_card',
        status='pending',
        payment_receipt__isnull=False,
    ).exclude(payment_receipt='').update(status='c2c_pending')


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0044_catalog_digital_access'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalogorder',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'در انتظار پرداخت'),
                    ('c2c_pending', 'در انتظار تأیید کارت به کارت'),
                    ('paid', 'پرداخت\u200cشده'),
                    ('failed', 'ناموفق'),
                    ('cancelled', 'لغوشده'),
                    ('request', 'درخواست'),
                ],
                db_index=True,
                default='pending',
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_card_to_card_receipt_orders, migrations.RunPython.noop),
    ]
