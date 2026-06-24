from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0038_card_to_card_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriber',
            name='flow_state',
            field=models.JSONField(blank=True, default=dict, help_text='حالت موقت جریان (ورودی، فرم، رهگیری سفارش و …).'),
        ),
        migrations.AddField(
            model_name='catalogitem',
            name='compare_at_price',
            field=models.PositiveBigIntegerField(blank=True, help_text='قیمت قبل از تخفیف (برای نمایش خط‌خورده)', null=True),
        ),
        migrations.AddField(
            model_name='catalogitem',
            name='sales_count',
            field=models.PositiveIntegerField(default=0, help_text='تعداد فروش موفق (برای پرفروش‌ترین‌ها)'),
        ),
    ]
