from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0029_workspace_allow_instagram'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogsettings',
            name='hero_background',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='catalog/%Y/%m/',
                verbose_name='تصویر پس‌زمینه هیرو',
            ),
        ),
    ]
