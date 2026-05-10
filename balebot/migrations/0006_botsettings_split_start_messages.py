# Generated manually for data-preserving field split

from django.db import migrations, models


def forwards_copy_start_messages(apps, schema_editor):
    BotSettings = apps.get_model('balebot', 'BotSettings')
    for row in BotSettings.objects.all():
        w = row.welcome_message or ''
        cp = (row.contact_prompt_message or '').strip()
        row.start_message_normal = w
        row.start_message_contact = (w + '\n\n' + cp).strip() if cp else w
        row.save(update_fields=['start_message_normal', 'start_message_contact'])


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0005_campaign_schedule_kind'),
    ]

    operations = [
        migrations.AddField(
            model_name='botsettings',
            name='start_message_normal',
            field=models.TextField(default='', verbose_name='پیام /start معمولی'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='botsettings',
            name='start_message_contact',
            field=models.TextField(default='', verbose_name='پیام /start هنگام درخواست شماره'),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_copy_start_messages, lambda apps, schema_editor: None),
        migrations.RemoveField(
            model_name='botsettings',
            name='welcome_message',
        ),
        migrations.RemoveField(
            model_name='botsettings',
            name='contact_prompt_message',
        ),
        migrations.AlterField(
            model_name='botsettings',
            name='start_message_normal',
            field=models.TextField(
                default=(
                    'سلام! خوش آمدید.\n'
                    'می‌توانید از منوی زیر استفاده کنید و اطلاعیه‌ها را دریافت کنید.'
                ),
                help_text=(
                    'برای کاربرانی که قبلاً شماره داده‌اند، یا وقتی گزینهٔ «دریافت شماره بعد از /start» خاموش است.'
                ),
                verbose_name='پیام /start معمولی',
            ),
        ),
        migrations.AlterField(
            model_name='botsettings',
            name='start_message_contact',
            field=models.TextField(
                default=(
                    'سلام! برای تکمیل ثبت‌نام و دریافت اطلاعیه‌ها، شمارهٔ خود را '
                    'با دکمهٔ زیر ارسال کنید.'
                ),
                help_text=(
                    'فقط برای کاربرانی که هنوز شماره نداده‌اند، وقتی گزینهٔ دریافت شماره روشن باشد. '
                    'اگر منوی اینلاین هم دارید، این متن در پیام اول با اینلاین می‌آید؛ پیام بعد فقط دکمهٔ تماس است.'
                ),
                verbose_name='پیام /start هنگام درخواست شماره',
            ),
        ),
    ]
