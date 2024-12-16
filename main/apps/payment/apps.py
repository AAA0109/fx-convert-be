from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.payment'

    def ready(self) -> None:
        import main.apps.payment.signals.handlers  # noqa
