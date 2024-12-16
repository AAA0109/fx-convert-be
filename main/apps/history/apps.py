from django.apps import AppConfig


class HistoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.history'

    def ready(self) -> None:
        import main.apps.history.signals.handlers #noqa
