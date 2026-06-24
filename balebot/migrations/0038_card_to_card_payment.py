from django.db import migrations, models


def migrate_zarinpal_to_card_to_card(apps, schema_editor):
    CatalogSettings = apps.get_model('balebot', 'CatalogSettings')
    CatalogOrder = apps.get_model('balebot', 'CatalogOrder')
    CatalogSettings.objects.filter(payment_default_method='zarinpal').update(
        payment_default_method='card_to_card',
    )
    CatalogOrder.objects.filter(payment_method='zarinpal').update(
        payment_method='card_to_card',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0037_resync_store_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogsettings',
            name='payment_card_to_card_enabled',
            field=models.BooleanField(default=False, verbose_name='فعال\u200cسازی کارت به کارت'),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='card_to_card_number',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='شماره کارت'),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='card_to_card_sheba',
            field=models.CharField(blank=True, default='', max_length=34, verbose_name='شماره شبا'),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='card_to_card_holder',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='نام صاحب حساب'),
        ),
        migrations.AddField(
            model_name='catalogorder',
            name='payment_receipt',
            field=models.ImageField(blank=True, null=True, upload_to='catalog/receipts/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='catalogorder',
            name='receipt_uploaded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_zarinpal_to_card_to_card, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='catalogsettings',
            name='payment_zarinpal_enabled',
        ),
        migrations.RemoveField(
            model_name='catalogsettings',
            name='zarinpal_merchant_id',
        ),
        migrations.RemoveField(
            model_name='catalogsettings',
            name='zarinpal_sandbox',
        ),
        migrations.RemoveField(
            model_name='catalogorder',
            name='zarinpal_authority',
        ),
        migrations.AlterField(
            model_name='catalogsettings',
            name='payment_default_method',
            field=models.CharField(
                choices=[
                    ('admin_cart', 'ارسال سبد به ادمین'),
                    ('card_to_card', 'کارت به کارت'),
                    ('bale', 'پرداخت بله'),
                ],
                default='admin_cart',
                max_length=16,
                verbose_name='روش پرداخت پیش\u200cفرض',
            ),
        ),
    ]
