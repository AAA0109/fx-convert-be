from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.billing'

    def ready(self) -> None:
        import main.apps.billing.signals.handlers
