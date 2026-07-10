# Generated manually for ShowcaseBot model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0005_alter_landingsettings_brand_favicon_svg_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShowcaseBot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='نام ربات')),
                ('image', models.ImageField(help_text='تصویر نمایشی ربات (مربعی یا افقی).', upload_to='showcase_bots/', verbose_name='تصویر')),
                ('description', models.TextField(verbose_name='توضیحات')),
                ('platform', models.CharField(choices=[('bale', 'بله'), ('telegram', 'تلگرام')], max_length=20, verbose_name='پیام\u200cرسان')),
                ('bot_url', models.URLField(max_length=500, verbose_name='لینک ربات')),
                ('show_on_landing', models.BooleanField(default=False, help_text='اگر فعال باشد، در صفحه اصلی نمایش داده می\u200cشود.', verbose_name='نمایش در لندینگ')),
                ('is_active', models.BooleanField(default=True, help_text='غیرفعال = در هیچ صفحه\u200cای نمایش داده نمی\u200cشود.', verbose_name='فعال')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='ترتیب')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'ربات نمایشی',
                'verbose_name_plural': 'ربات\u200cهای نمایشی',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
