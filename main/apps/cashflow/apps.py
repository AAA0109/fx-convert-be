from django.apps import AppConfig


class CashflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.cashflow'

    def ready(self) -> None:
        import main.apps.cashflow.signals.handlers  # noqa
