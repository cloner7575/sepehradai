from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0003_botsettings_start_keyboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriber',
            name='menu_flow_log',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='تاریخچهٔ کلیک‌های منوی /start (آخرین مراحل).',
            ),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='menu_flow_answers',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='پاسخ‌های نام‌دار (flow_key) از دکمه‌های منو.',
            ),
        ),
    ]
