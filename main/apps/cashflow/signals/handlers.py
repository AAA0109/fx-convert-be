from django.db.models.signals import pre_save
from django.dispatch import receiver

from main.apps.cashflow.models import SingleCashFlow
from main.apps.oems.models import Ticket


@receiver(pre_save, sender=SingleCashFlow)
def update_single_cashflow_tickets(sender, instance, **kwargs):
    # Check if the ticket_id has been modified
    if instance.pk is not None:  # Ensure it's not a new instance
        if instance.ticket_id is None:
            instance.tickets.clear()
        old_instance = SingleCashFlow.objects.get(pk=instance.pk)
        if old_instance.ticket_id != instance.ticket_id:
            if instance.ticket_id:
                try:
                    ticket = Ticket.objects.get(ticket_id=instance.ticket_id)
                    instance.tickets.set([ticket])
                except Ticket.DoesNotExist:
                    # Handle the case when the corresponding ticket doesn't exist
                    instance.tickets.clear()
            else:
                instance.tickets.clear()
