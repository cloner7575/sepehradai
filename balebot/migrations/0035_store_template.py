from django.db import migrations, models


def seed_store_templates(apps, schema_editor):
    StoreTemplate = apps.get_model('balebot', 'StoreTemplate')
    from balebot.data.store_templates_seed import STORE_TEMPLATES

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


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0034_catalog_bale_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=80, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('industry', models.CharField(db_index=True, max_length=60)),
                ('description', models.CharField(blank=True, default='', max_length=255)),
                ('preview_image', models.ImageField(blank=True, upload_to='store_templates/')),
                ('data', models.JSONField(blank=True, default=dict)),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'الگوی فروشگاه',
                'verbose_name_plural': 'الگوهای فروشگاه',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.RunPython(seed_store_templates, migrations.RunPython.noop),
    ]
