from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from main.apps.broker.models import Broker


class EntitySyncEntity(TimeStampedModel):
    class SyncEntityType(models.TextChoices):
        BENEFICIARY = "beneficiary", _("Beneficiary")
        WALLET = "wallet", _("Wallet")

    entity_type = models.CharField(
        max_length=20,
        choices=SyncEntityType.choices,
        help_text="The type of entity being synced (beneficiary or wallet)"
    )
    entity_id = models.CharField(
        max_length=100,
        help_text="The unique identifier of the entity being synced"
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The timestamp of the last sync"
    )

    class Meta:
        unique_together = ("entity_type", "entity_id", "broker")

    def __str__(self):
        return f"{self.entity_type} - {self.entity_id} - {self.broker.name}"


class EntitySyncResult(TimeStampedModel):
    entity = models.ForeignKey(EntitySyncEntity, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    error = models.JSONField()
    result = models.JSONField()

    class SyncStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PARTIALLY_SYNCED = "partially_synced", _("Partially Synced")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")

    status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        help_text="The status of the sync operation"
    )
