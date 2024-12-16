from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DataproviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.dataprovider'
    verbose_name = "Data Provider Config"

    def ready(self):
        super(DataproviderConfig, self).ready()
        import main.apps.dataprovider.signals.handlers
