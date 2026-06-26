from landing.services.public_content import default_demo_bot_url


def landing_settings(request):
    return {
        'LANDING_DEMO_BOT_URL': default_demo_bot_url(),
    }
