# Multi-tenant workspace isolation

import secrets

from django.conf import settings as django_settings
from django.db import migrations, models
import django.db.models.deletion


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)[:64]


def backfill_workspaces(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Workspace = apps.get_model('balebot', 'Workspace')
    BotSettings = apps.get_model('balebot', 'BotSettings')
    Subscriber = apps.get_model('balebot', 'Subscriber')
    Tag = apps.get_model('balebot', 'Tag')
    Campaign = apps.get_model('balebot', 'Campaign')
    FlowMedia = apps.get_model('balebot', 'FlowMedia')

    owner = (
        User.objects.filter(is_superuser=True).order_by('id').first()
        or User.objects.filter(is_staff=True).order_by('id').first()
        or User.objects.order_by('id').first()
    )
    if owner is None:
        return

    ws = Workspace.objects.filter(owner_id=owner.id).first()
    if ws is None:
        ws = Workspace.objects.create(name='اصلی', owner_id=owner.id, is_active=True)

    for model in (BotSettings, Subscriber, Tag, Campaign, FlowMedia):
        model.objects.filter(workspace__isnull=True).update(workspace_id=ws.id)

    used_secrets: set[str] = set()
    for cfg in BotSettings.objects.all().order_by('id'):
        secret = (cfg.webhook_secret or '').strip()
        if not secret or secret in used_secrets:
            while True:
                secret = _generate_secret()
                if secret not in used_secrets:
                    break
            cfg.webhook_secret = secret
            cfg.save(update_fields=['webhook_secret'])
        used_secrets.add(secret)

    for platform in ('bale', 'telegram'):
        if not BotSettings.objects.filter(workspace_id=ws.id, platform=platform).exists():
            BotSettings.objects.create(
                workspace_id=ws.id,
                platform=platform,
                webhook_secret=_generate_secret(),
                panel_brand_title='کنترل بازو' if platform == 'bale' else 'کنترل تلگرام',
                panel_brand_subtitle='مدیریت کمپین و مخاطبان',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('balebot', '0015_botsettings_fixed_pk'),
        migrations.swappable_dependency(django_settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='نام پنل')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'owner',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workspace',
                        to=django_settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'فضای کاری',
                'verbose_name_plural': 'فضاهای کاری',
                'ordering': ['name'],
            },
        ),
        migrations.RemoveConstraint(
            model_name='subscriber',
            name='unique_subscriber_platform_user',
        ),
        migrations.RemoveConstraint(
            model_name='tag',
            name='unique_tag_platform_slug',
        ),
        migrations.RemoveConstraint(
            model_name='tag',
            name='unique_tag_platform_name',
        ),
        migrations.AlterField(
            model_name='botsettings',
            name='platform',
            field=models.CharField(
                choices=[('bale', 'بله'), ('telegram', 'تلگرام')],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='botsettings',
            name='workspace',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bot_settings',
                to='balebot.workspace',
            ),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='workspace',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subscribers',
                to='balebot.workspace',
            ),
        ),
        migrations.AddField(
            model_name='tag',
            name='workspace',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tags',
                to='balebot.workspace',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='workspace',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='campaigns',
                to='balebot.workspace',
            ),
        ),
        migrations.AddField(
            model_name='flowmedia',
            name='workspace',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='flow_media',
                to='balebot.workspace',
            ),
        ),
        migrations.RunPython(backfill_workspaces, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='botsettings',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bot_settings',
                to='balebot.workspace',
            ),
        ),
        migrations.AlterField(
            model_name='subscriber',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subscribers',
                to='balebot.workspace',
            ),
        ),
        migrations.AlterField(
            model_name='tag',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tags',
                to='balebot.workspace',
            ),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='campaigns',
                to='balebot.workspace',
            ),
        ),
        migrations.AlterField(
            model_name='flowmedia',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='flow_media',
                to='balebot.workspace',
            ),
        ),
        migrations.AlterField(
            model_name='botsettings',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='botsettings',
            name='webhook_secret',
            field=models.CharField(
                blank=True,
                default='',
                help_text='بخش secret در URL وب‌هوک.',
                max_length=128,
                unique=True,
                verbose_name='رمز وب‌هوک',
            ),
        ),
        migrations.AddConstraint(
            model_name='botsettings',
            constraint=models.UniqueConstraint(
                fields=('workspace', 'platform'),
                name='unique_botsettings_workspace_platform',
            ),
        ),
        migrations.AddConstraint(
            model_name='subscriber',
            constraint=models.UniqueConstraint(
                fields=('workspace', 'platform', 'messenger_user_id'),
                name='unique_subscriber_workspace_platform_user',
            ),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(
                fields=('workspace', 'platform', 'slug'),
                name='unique_tag_workspace_platform_slug',
            ),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(
                fields=('workspace', 'platform', 'name'),
                name='unique_tag_workspace_platform_name',
            ),
        ),
    ]
