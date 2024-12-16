from django.apps import AppConfig


class OemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.oems'
    verbose_name = 'Payments & OEMS'

    def ready(self) -> None:
        super(OemsConfig, self).ready()
