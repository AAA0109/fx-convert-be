from django.apps import AppConfig

import main.settings.base as settings


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.account'
    verbose_name = 'Quick Account'

    def ready(self):
        super(AccountConfig, self).ready()
        import main.apps.account.signals.handlers # noqa: F401
        if settings.pubsub.get('TOPIC_ID') is not None and settings.pubsub.get('GC_CREDENTIALS_PATH') is not None:
            import main.libs.pubsub.config
            import main.apps.account.models.signals
            main.libs.pubsub.config.init(settings.pubsub)
