# Generated manually for start inline keyboard + contact prompt

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0002_botsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='botsettings',
            name='start_inline_keyboard',
            field=models.JSONField(blank=True, default=dict, help_text='دکمه‌های اینلاین پس از /start: بخش‌ها و ردیف‌ها (همان ساختار کمپین) + نوع اکشن برای هر دکمه.'),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='contact_prompt_message',
            field=models.TextField(
                blank=True,
                default='',
                help_text='وقتی هم دکمهٔ اینلاین /start و هم دکمهٔ تماس فعال باشد، این متن در پیام دوم قبل از صفحه‌کلید تماس ارسال می‌شود.',
                verbose_name='پیام جدا برای درخواست شماره',
            ),
        ),
    ]
