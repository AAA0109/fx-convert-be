from django.db.models.signals import pre_save
from django.dispatch import receiver

from main.apps.dataprovider.models.collector_config import StorageConfig


@receiver(pre_save, sender=StorageConfig)
def handle_storage_config_pre_save(sender, instance, **kwargs):
    if not instance.name:
        parts = []
        if instance.writer:
            parts.append(instance.writer.split('.')[-1])
        if instance.publisher:
            parts.append(instance.publisher.split('.')[-1])
        if instance.cache:
            parts.append(instance.cache.split('.')[-1])
        instance.name = ' | '.join(parts)
