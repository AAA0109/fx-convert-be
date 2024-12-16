from django.apps import AppConfig


class SettlementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.settlement'

    def ready(self):
        import main.apps.settlement.signals  # noqa
