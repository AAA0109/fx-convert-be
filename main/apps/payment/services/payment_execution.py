from typing import List, Sequence

from django.db import transaction
from rest_framework import status
from rest_framework.request import Request

from main.apps.account.models import User
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.services.trading import RfqExecutionProvider, trading_provider
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.ticket_payload import RfqErrorProvider, TicketPayloadProvider


class PaymentExecutionService:
    payment: Payment

    def __init__(self, payment: Payment, request: Request) -> None:
        self.payment = payment
        self.request = request

    def execute(self) -> dict:
        try:
            with transaction.atomic():
                if self.payment.execution_timing == Payment.ExecutionTiming.SCHEDULED:
                    response = self.execute_non_rfq_payment()
                    self.payment.payment_status = Payment.PaymentStatus.SCHEDULED
                elif self.payment.execution_timing == Payment.ExecutionTiming.STRATEGIC_EXECUTION:
                    # what do we want to call this
                    response = self.execute_non_rfq_payment()
                    self.payment.payment_status = Payment.PaymentStatus.STRATEGIC_EXECUTION
                elif self.payment.cashflow_generator.buy_currency == self.payment.cashflow_generator.sell_currency:
                    response = self.execute_non_rfq_payment()
                    self.payment.payment_status = Payment.PaymentStatus.WORKING
                else:
                    response = self.execute_rfq_payment()
                    self.payment.payment_status = Payment.PaymentStatus.WORKING
                self.payment.save()
                return response
        except Exception as e:
            raise e

    def get_tickets(self) -> Sequence[Ticket]:
        cashflows = SingleCashFlow.objects.filter(generator=self.payment.cashflow_generator)
        cashflow_ids = []
        for cashflow in cashflows:
            cashflow_ids.append(cashflow.cashflow_id)
        tickets = Ticket.objects.filter(cashflow_id__in=cashflow_ids)
        return tickets

    def generate_ticket_execution_payload(self, is_rfq=False) -> List[dict]:
        payload = []
        tickets = self.get_tickets()
        auth_user = None
        if self.user_can_execute(self.request.user):
            auth_user = self.request.user

        if tickets.exists():
            for ticket in tickets:
                req_body = TicketPayloadProvider.get_ticket_execution_payload(payment=self.payment, ticket=ticket, auth_user=auth_user)
                payload.append(req_body)
            return payload

        if not is_rfq and len(list(tickets)) == 0:
            cashflows = SingleCashFlow.objects.filter(generator=self.payment.cashflow_generator)
            for cashflow in cashflows:
                req_body = TicketPayloadProvider.get_ticket_execution_payload(payment=self.payment, cashflow=cashflow, auth_user=auth_user)
                payload.append(req_body)
        return payload

    def build_response(self, responses: List[dict]) -> dict:
        response_built = {
            'success': [],
            'error': []
        }

        for response in responses:
            if response['status'] in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED]:
                response_built['success'].append(response['data'])
                continue
            error = RfqErrorProvider.construct_from_execute_error_response(error=response)
            response_built['error'].append(error)
        return response_built

    def execute_rfq_payment(self) -> dict:
        payloads = self.generate_ticket_execution_payload(is_rfq=True)
        multiple_responses = trading_provider.execute_rfq(user=self.request.user, request=payloads)
        return self.build_response(responses=multiple_responses.data)

    def execute_non_rfq_payment(self) -> dict:
        payloads = self.generate_ticket_execution_payload()
        multiple_responses = trading_provider.execute(user=self.request.user, request=payloads)
        return self.build_response(responses=multiple_responses.data)

    def user_can_execute(self, user: User):
        #TODO: Once approvals are in place we need to check if the user have permission here to execute
        return True



class BulkPaymentExecutionService:

    @staticmethod
    def bulk_payment_execution(request: Request, payment_ids: List[int]) -> List[dict]:
        with transaction.atomic():
            bulk_execution_status = []
            payments = Payment.objects.filter(id__in=payment_ids)
            for payment in payments:
                execution_service = PaymentExecutionService(payment=payment, request=request)
                execution_status = execution_service.execute()
                bulk_execution_status.append({
                    'payment_id': payment.pk,
                    'execution_status': execution_status
                })
            return bulk_execution_status
