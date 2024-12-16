from django.apps import AppConfig


class MarginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.margin'
    def ready(self) -> None:
        import main.apps.margin.signals.handlers #noqa
