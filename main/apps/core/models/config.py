from django.db import models


class Config(models.Model):
    path = models.CharField(max_length=255, null=False, unique=True)
    value = models.JSONField(null=False)

    @staticmethod
    def set_config(path, value):
        config = Config(path=path, value=value)
        config.save()

    @staticmethod
    def get_config(path):
        return Config.objects.filter(path=path).get()
