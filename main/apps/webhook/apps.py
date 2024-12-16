from django.apps import AppConfig


class WebhookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.webhook'
    verbose_name = 'API & Webhooks'
