from django.db import migrations


def resync_store_templates(apps, schema_editor):
    StoreTemplate = apps.get_model('balebot', 'StoreTemplate')
    from balebot.data.store_templates_seed import STORE_TEMPLATES

    active_slugs = set()
    for row in STORE_TEMPLATES:
        StoreTemplate.objects.update_or_create(
            slug=row['slug'],
            defaults={
                'name': row['name'],
                'industry': row['industry'],
                'description': row.get('description', ''),
                'sort_order': row.get('sort_order', 0),
                'data': row.get('data') or {},
                'is_active': True,
            },
        )
        active_slugs.add(row['slug'])

    StoreTemplate.objects.exclude(slug__in=active_slugs).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0036_catalog_store_features'),
    ]

    operations = [
        migrations.RunPython(resync_store_templates, migrations.RunPython.noop),
    ]
