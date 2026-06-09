from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0026_remove_digital_item_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriber',
            name='miniapp_first_seen_at',
            field=models.DateTimeField(
                blank=True,
                help_text='اولین بازدید از مینی‌اپ فروشگاه.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='require_channel_membership',
            field=models.BooleanField(default=False, verbose_name='الزام عضویت در کانال'),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='required_channel_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='@username کانال یا شناسه عددی. ربات باید ادمین کانال باشد.',
                max_length=128,
                verbose_name='شناسه کانال',
            ),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='channel_membership_message',
            field=models.TextField(
                blank=True,
                default='برای استفاده از فروشگاه ابتدا در کانال ما عضو شوید.',
                verbose_name='پیام عضویت کانال',
            ),
        ),
        migrations.AddField(
            model_name='catalogsettings',
            name='channel_invite_link',
            field=models.URLField(
                blank=True,
                default='',
                verbose_name='لینک پیوستن به کانال',
            ),
        ),
    ]
