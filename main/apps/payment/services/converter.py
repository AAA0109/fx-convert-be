import logging

from typing import List, Tuple
from rest_framework.exceptions import ValidationError
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.ticket_payload import RfqErrorProvider, TicketPayloadProvider

logger = logging.getLogger(__name__)

class PaymentToTicketConverter:
    payment: Payment

    def __init__(self, payment:Payment) -> None:
        self.payment = payment

    def convert_to_tickets(self) -> Tuple[List[Ticket], List[dict]]:
        tickets = []
        errors = []
        single_cashflows = SingleCashFlow.objects.filter(generator=self.payment.cashflow_generator)
        for single_cashflow in single_cashflows:

            try:
                existing_ticket = Ticket.objects.get(cashflow_id=single_cashflow.cashflow_id)
                tickets.append(existing_ticket)
                continue
            except Ticket.DoesNotExist as e:
                pass

            try:
                ticket = self.__single_cashflow_to_ticket(cashflow=single_cashflow)
                single_cashflow.status = SingleCashFlow.Status.LIVE
                single_cashflow.ticket_id = ticket.ticket_id
                single_cashflow.save()
                tickets.append(ticket)
            except ValidationError as e:
                error = RfqErrorProvider.construct_from_ticket_validation_error(e=e, cashflow=single_cashflow)
                errors.append(error)
            except Exception as e:
                logger.exception(e)
                error = RfqErrorProvider.construct_from_ticket_validation_error(e=e, cashflow=single_cashflow)
                errors.append(error)

        self.payment.cashflow_generator.status = CashFlowGenerator.Status.LIVE
        self.payment.cashflow_generator.save()

        self.payment_status = Payment.PaymentStatus.WORKING
        self.payment.save()

        return tickets, errors

    def __single_cashflow_to_ticket(self, cashflow: SingleCashFlow) -> Ticket:
        payload = TicketPayloadProvider.get_create_ticket_attributes(payment=self.payment, cashflow=cashflow)
        ticket: Ticket = Ticket._create(**payload)
        ticket.save()
        return ticket
