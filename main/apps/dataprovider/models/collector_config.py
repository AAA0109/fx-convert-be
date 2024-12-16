from django.db import models
from django_extensions.db.models import TimeStampedModel


class StorageConfig(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    writer = models.CharField(max_length=1024, null=True, blank=True)
    publisher = models.CharField(max_length=1024, null=True, blank=True)
    cache = models.CharField(max_length=1024, null=True, blank=True)
    def __str__(self):
        return self.name


class CollectorConfig(TimeStampedModel):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    collector = models.CharField(max_length=255)
    storage_config = models.ForeignKey(StorageConfig, on_delete=models.CASCADE)
    kwargs = models.JSONField(default=dict)

    def __str__(self):
        return self.name
