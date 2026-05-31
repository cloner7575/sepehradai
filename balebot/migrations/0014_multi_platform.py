# Generated manually for multi-platform support

import os

from django.db import migrations, models


def migrate_env_to_bale_settings(apps, schema_editor):
    BotSettings = apps.get_model('balebot', 'BotSettings')
    bale = BotSettings.objects.filter(platform='bale').first()
    if bale is None:
        bale = BotSettings.objects.order_by('id').first()
        if bale is not None:
            bale.platform = 'bale'
            bale.save(update_fields=['platform'])

    if bale is not None:
        token = os.environ.get('BALE_BOT_TOKEN', '').strip()
        secret = os.environ.get('BALE_WEBHOOK_SECRET', '').strip()
        public_url = os.environ.get('BALE_WEBHOOK_PUBLIC_URL', '').strip()
        updated = []
        if token and not bale.bot_token:
            bale.bot_token = token
            updated.append('bot_token')
        if secret and not bale.webhook_secret:
            bale.webhook_secret = secret
            updated.append('webhook_secret')
        if public_url and not bale.webhook_public_url:
            bale.webhook_public_url = public_url
            updated.append('webhook_public_url')
        if updated:
            bale.save(update_fields=updated)

    if not BotSettings.objects.filter(platform='telegram').exists():
        BotSettings.objects.create(
            id=2,
            platform='telegram',
            panel_brand_title='کنترل تلگرام',
            panel_brand_subtitle='مدیریت کمپین و مخاطبان',
        )


def migrate_legacy_botsettings_pk(apps, schema_editor):
    BotSettings = apps.get_model('balebot', 'BotSettings')
    legacy = BotSettings.objects.filter(platform__isnull=True).first()
    if legacy is None:
        return
    existing = BotSettings.objects.filter(platform='bale').exclude(pk=legacy.pk).first()
    if existing:
        for field in (
            'panel_brand_title', 'panel_brand_subtitle', 'start_message_normal',
            'contact_button_label', 'registration_success_message', 'unsubscribe_message',
            'callback_ack_message', 'help_message', 'start_inline_keyboard', 'start_flow',
            'start_flow_default_text', 'start_message_contact', 'collect_contact_on_start',
            'enable_help_command', 'enable_stop_command', 'enable_support',
            'support_button_label', 'support_start_prompt_message', 'support_waiting_message',
        ):
            setattr(existing, field, getattr(legacy, field))
        existing.save()
        legacy.delete()
    else:
        legacy.platform = 'bale'
        legacy.save(update_fields=['platform'])


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0013_migrate_start_keyboard_to_flow'),
    ]

    operations = [
        migrations.RenameField(
            model_name='flowmedia',
            old_name='bale_file_id',
            new_name='messenger_file_id',
        ),
        migrations.RenameField(
            model_name='inboundmessage',
            old_name='bale_message_id',
            new_name='messenger_message_id',
        ),
        migrations.RenameField(
            model_name='subscriber',
            old_name='bale_user_id',
            new_name='messenger_user_id',
        ),
        migrations.AddField(
            model_name='botsettings',
            name='bot_token',
            field=models.CharField(blank=True, default='', help_text='از BotFather دریافت می‌شود.', max_length=256, verbose_name='توکن ربات'),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='is_enabled',
            field=models.BooleanField(default=True, help_text='اگر خاموش باشد وب‌هوک پاسخ نمی‌دهد.', verbose_name='فعال'),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='webhook_public_url',
            field=models.URLField(blank=True, default='', help_text='مثلاً https://example.com — بدون اسلش پایانی.', verbose_name='آدرس عمومی سرور'),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='webhook_secret',
            field=models.CharField(blank=True, default='', help_text='بخش secret در URL وب‌هوک.', max_length=128, verbose_name='رمز وب‌هوک'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                default='bale',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='flowmedia',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                default='bale',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                default='bale',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='tag',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                default='bale',
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_legacy_botsettings_pk, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='botsettings',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                max_length=16,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='tag',
            name='name',
            field=models.CharField(max_length=120),
        ),
        migrations.AlterField(
            model_name='tag',
            name='slug',
            field=models.SlugField(max_length=140),
        ),
        migrations.AlterUniqueTogether(
            name='tag',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='subscriber',
            name='messenger_user_id',
            field=models.BigIntegerField(db_index=True),
        ),
        migrations.AddConstraint(
            model_name='subscriber',
            constraint=models.UniqueConstraint(
                fields=('platform', 'messenger_user_id'),
                name='unique_subscriber_platform_user',
            ),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(fields=('platform', 'slug'), name='unique_tag_platform_slug'),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(fields=('platform', 'name'), name='unique_tag_platform_name'),
        ),
        migrations.RunPython(migrate_env_to_bale_settings, migrations.RunPython.noop),
    ]
