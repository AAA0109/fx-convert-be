from django.apps import AppConfig


class BrokerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.broker'
    verbose_name = 'Broker Configuration'

    def ready(self):
        import main.apps.broker.signals  # noqa: F401
