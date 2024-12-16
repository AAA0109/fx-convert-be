from django.apps import AppConfig


class IbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.ibkr'

    def ready(self) -> None:
        import main.apps.ibkr.signals.handlers #noqa
