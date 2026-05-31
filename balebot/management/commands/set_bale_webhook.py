from django.core.management.base import BaseCommand

from balebot.management.commands.set_webhook import Command as SetWebhookCommand


class Command(SetWebhookCommand):
    help = 'فراخوانی setWebhook برای بازوی بله (alias — از set_webhook --platform bale استفاده کنید)'

    def handle(self, *args, **options):
        options['platform'] = 'bale'
        return super().handle(*args, **options)
