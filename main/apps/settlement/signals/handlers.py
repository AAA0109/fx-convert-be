from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from main.apps.oems.backend.webhook import WEBHOOK_EVENTS
from main.apps.settlement.api.serializers.beneficiary import BeneficiarySerializer
from main.apps.settlement.models import Beneficiary
from main.apps.webhook.models import Webhook


@receiver(post_save, sender=Beneficiary)
def post_save_beneficiary_handler(sender, instance: Beneficiary, created, **kwargs):
    serializer = BeneficiarySerializer(instance)
    payload = serializer.data
    if created:
        Webhook.dispatch_event(instance.company, WEBHOOK_EVENTS.BENEFICIARY_CREATED, payload)
    else:
        Webhook.dispatch_event(instance.company, WEBHOOK_EVENTS.BENEFICIARY_UPDATED, payload)


@receiver(post_delete, sender=Beneficiary)
def post_delete_beneficiary_handler(sender, instance: Beneficiary, **kwargs):
    serializer = BeneficiarySerializer(instance)
    payload = serializer.data
    Webhook.dispatch_event(instance.company, WEBHOOK_EVENTS.BENEFICIARY_DELETED, payload)
