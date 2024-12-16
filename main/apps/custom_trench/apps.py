from trench.apps import TrenchConfig


class CustomTrenchConfig(TrenchConfig):
    default_auto_field = 'django.db.models.AutoField'
