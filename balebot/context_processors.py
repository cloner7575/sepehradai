from django.db.utils import OperationalError


def panel_branding(_request):
    try:
        from balebot.models import BotSettings

        return {'bot_branding': BotSettings.get_solo()}
    except OperationalError:
        return {'bot_branding': None}
