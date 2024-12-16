from django.apps import AppConfig


class PricingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.pricing'

    def ready(self):
        super(PricingConfig, self).ready()
        import main.apps.pricing.signals.handlers
