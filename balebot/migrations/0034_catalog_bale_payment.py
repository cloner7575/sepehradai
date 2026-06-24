import uuid

from django.db import migrations, models


def _order_public_token():
    return uuid.uuid4().hex


def fill_order_public_tokens(apps, schema_editor):
    CatalogOrder = apps.get_model('balebot', 'CatalogOrder')
    seen: set[str] = set()
    for order in CatalogOrder.objects.all().iterator():
        token = (order.public_token or '').strip()
        if not token or token in seen:
            token = uuid.uuid4().hex
        while token in seen:
            token = uuid.uuid4().hex
        seen.add(token)
        if order.public_token != token:
            order.public_token = token
            order.save(update_fields=['public_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0033_remove_service_item_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogsettings',
            name='payment_bale_enabled',
            field=models.BooleanField(default=False, verbose_name='فعال\u200cسازی پرداخت بله'),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='bale_payment_card_number',
            field=models.CharField(
                blank=True,
                default='',
                help_text='به\u200cعنوان provider_token در sendInvoice استفاده می\u200cشود.',
                max_length=32,
                verbose_name='شماره کارت فروشنده (بله)',
            ),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='bale_payment_card_holder',
            field=models.CharField(
                blank=True,
                default='',
                max_length=128,
                verbose_name='نام دارنده کارت',
            ),
        ),
        migrations.AddField(
            model_name='catalogorder',
            name='public_token',
            field=models.CharField(blank=True, default='', editable=False, max_length=64),
        ),
        migrations.RunPython(fill_order_public_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='catalogorder',
            name='public_token',
            field=models.CharField(
                db_index=True,
                default=_order_public_token,
                editable=False,
                max_length=64,
                unique=True,
            ),
        ),
    ]
