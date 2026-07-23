from django.db import migrations, models


def _phone(value):
    table = str.maketrans(
        '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669',
        '01234567890123456789',
    )
    digits = ''.join(ch for ch in str(value or '').translate(table) if ch.isdigit())
    if digits.startswith('0098'):
        digits = '0' + digits[4:]
    elif digits.startswith('98'):
        digits = '0' + digits[2:]
    return digits[:20]


def forwards(apps, schema_editor):
    Customer = apps.get_model('balebot', 'CustomerProfile')
    Subscriber = apps.get_model('balebot', 'Subscriber')
    Item = apps.get_model('balebot', 'CatalogItem')
    Order = apps.get_model('balebot', 'CatalogOrder')
    Contact = apps.get_model('instagram', 'InstagramContact')

    for subscriber in Subscriber.objects.filter(customer__isnull=True).iterator():
        normalized = _phone(subscriber.phone_number)
        verified = getattr(subscriber, 'phone_verified_at', None)
        if not verified and normalized and subscriber.is_registered:
            verified = subscriber.created_at
            Subscriber.objects.filter(pk=subscriber.pk).update(phone_verified_at=verified)
        customer = None
        if normalized and verified:
            customer = Customer.objects.filter(
                workspace_id=subscriber.workspace_id,
                normalized_phone=normalized,
                phone_verified_at__isnull=False,
            ).first()
        if not customer:
            customer = Customer.objects.create(
                workspace_id=subscriber.workspace_id,
                display_name=(subscriber.first_name or subscriber.username or '')[:255],
                normalized_phone=normalized if verified else '',
                phone_verified_at=verified,
            )
        subscriber.customer_id = customer.pk
        subscriber.save(update_fields=['customer'])

    for contact in Contact.objects.filter(customer__isnull=True).iterator():
        customer_id = None
        if contact.subscriber_id:
            customer_id = Subscriber.objects.filter(pk=contact.subscriber_id).values_list('customer_id', flat=True).first()
        if not customer_id:
            customer_id = Customer.objects.create(
                workspace_id=contact.workspace_id,
                display_name=(contact.display_name or contact.username or '')[:255],
                metadata={'identity_source': 'instagram'},
            ).pk
        contact.customer_id = customer_id
        contact.save(update_fields=['customer'])

    for order in Order.objects.filter(customer__isnull=True).iterator():
        customer_id = None
        if order.subscriber_id:
            customer_id = Subscriber.objects.filter(pk=order.subscriber_id).values_list('customer_id', flat=True).first()
        if not customer_id and order.instagram_contact_id:
            customer_id = Contact.objects.filter(pk=order.instagram_contact_id).values_list('customer_id', flat=True).first()
        updates = []
        if customer_id:
            order.customer_id = customer_id
            updates.append('customer')
        if not order.source_channel:
            order.source_channel = order.platform
            updates.append('source_channel')
        if updates:
            order.save(update_fields=updates)

    for workspace_id, slug in Item.objects.values_list('workspace_id', 'slug').distinct():
        group = Item.objects.filter(workspace_id=workspace_id, slug=slug).order_by('pk')
        canonical = group.values_list('canonical_key', flat=True).first()
        if canonical:
            group.update(canonical_key=canonical)


class Migration(migrations.Migration):
    dependencies = [('balebot', '0046_catalogitem_canonical_key_and_more'), ('instagram', '0003_instagramconnection_auth_provider_and_more')]
    operations = [
        migrations.AddField(
            model_name='subscriber',
            name='phone_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
