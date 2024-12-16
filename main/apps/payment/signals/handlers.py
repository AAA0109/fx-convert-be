import logging
import uuid

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from main.apps.cashflow.models import SingleCashFlow
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.backend.ticket import Ticket as OEMSTicket
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.signals import oems_ticket_internal_state_change
from main.apps.payment.models import Payment


logger = logging.getLogger(__name__)



@receiver(oems_ticket_internal_state_change, sender=OEMSTicket,
          dispatch_uid='update_payment_status_from_oems_ticket_state')
@receiver(oems_ticket_internal_state_change, sender=Ticket,
          dispatch_uid='update_payment_status_from_django_ticket_state')
def update_payment_status_from_ticket_state(sender, instance: Ticket, state, **kwargs):
    logger.info(
        f"Received django signals - class: {sender.__class__} - instance {instance.__str__()}  - state: {state}")
    ticket = instance.as_django_model()
    try:
        # this is still not great as the ticket should update the cashflow state then call payment.eval_state()
        # to determine the state as the summary of cashflow states
        cashflows = SingleCashFlow.objects.filter(ticket_id=ticket.ticket_id)
        for cashflow in cashflows:
            # TODO: update cashflow states
            # payment could be multiple? need to update many <-> many
            payment = cashflow.generator.payment.first()
            if ticket.mass_payment_info:
                # loop through mass payment info
                # amounts = ticket.get_payment_amounts(use_lock_side=True)
                for info in ticket.mass_payment_info:
                    if info.get('cashflow_id') == cashflow.id:
                        logger.info('found cashflow for apportionment')
                        break # set stuff here
                # apportion
            else:
                amounts = ticket.get_payment_amounts(use_lock_side=True)
                payment.amount = amounts['amount']
                payment.cntr_amount = amounts['cntr_amount']
                payment.save()

            if ticket.action == Ticket.Actions.RFQ:
                continue
            payment_status = Payment.OEMS_STATE_MAPPING[state]

            if  ticket.execution_strategy == payment_status:
                ticket.internal_state = INTERNAL_STATES.WAITING
                ticket.execution_strategy = Ticket.ExecutionStrategies.STRATEGIC_EXECUTION
                payment.payment_status = Payment.PaymentStatus.STRATEGIC_EXECUTION
                payment.save()
                return

            if ticket.execution_strategy == Ticket.ExecutionStrategies.MARKET and ticket.execution_strategy in INTERNAL_STATES.WORKING_STATES:
                ticket.internal_state = INTERNAL_STATES.WAITING
                payment.payment_status = Payment.PaymentStatus.WORKING
                payment.save()
                return

            if payment_status != payment.payment_status:
                logger.info(
                    f"setting payment ({payment.id}) status from {payment.payment_status} to {Payment.OEMS_STATE_MAPPING[state]}")
                payment.payment_status = payment_status
                payment.save()
    except SingleCashFlow.DoesNotExist:
        return
    except Exception as e:
        logger.error(e)


@receiver(pre_delete, sender=SingleCashFlow, dispatch_uid='cancel_ticket_on_cashflow_delete')
def cancel_ticket_on_cashflow_delete(sender, instance:SingleCashFlow, using, **kwargs):
    if instance.ticket_id:
        from main.apps.payment.tasks.cancel_ticket import cancel_single_ticket_task

        celery_task_id = uuid.uuid4()
        cancel_single_ticket_task.apply_async(
            kwargs={'ticket_id':instance.ticket_id.__str__()},
            task_id=celery_task_id
        )


@receiver(post_save, sender=Payment, dispatch_uid='cancel_ticket_on_payment_delete')
def cancel_ticket_on_payment_delete(sender, instance:Payment, created, **kwargs):
    if not created and instance.payment_status == Payment.PaymentStatus.CANCELED:
        from main.apps.payment.tasks.cancel_ticket import bulk_ticket_cancel_task

        celery_task_id = uuid.uuid4()
        bulk_ticket_cancel_task.apply_async(
            kwargs={'payment_id':instance.pk},
            task_id=celery_task_id
        )
