import json
import logging
from typing import List

from django.db import transaction
from rest_framework import status
from rest_framework.request import Request
from rest_framework import serializers
from main.apps.approval.services.approval import CompanyApprovalService
from main.apps.approval.services.limit import CompanyLimitService
from main.apps.approval.services.payment_approval import PaymentApprovalService
from main.apps.broker.services.fee import BrokerFeeProvider

from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.oems.api.utils.response import ErrorResponse, MultiResponse
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.services.trading import trading_provider
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.converter import PaymentToTicketConverter
from main.apps.payment.services.ticket_payload import RfqErrorProvider, TicketPayloadProvider

logger = logging.getLogger(__name__)


class PaymentRfqService:
    ADDITIONAL_FIELDS = ['transaction_amount',
                         'delivery_fee', 'total_cost', 'indicative']
    payment: Payment

    def __init__(self, payment: Payment) -> None:
        self.payment = payment

    def get_cashflow(self) -> List[SingleCashFlow]:
        return SingleCashFlow.objects.filter(generator=self.payment.cashflow_generator)

    def validate_transaction_limit_and_approval(self):
        cashflows = self.get_cashflow()
        approval_svc = CompanyApprovalService(company=self.payment.company)
        limit_service = CompanyLimitService(company=self.payment.company)
        for cashflow in cashflows:
            discounted_amount, exceeding_limit = limit_service.validate_transaction_limit(amount=cashflow.amount,
                                                                                          currency=cashflow.lock_side,
                                                                                          value_date=cashflow.pay_date)

            is_tenor_exceeding_limit = limit_service.is_tenor_exceeding_limit(value_date=cashflow.pay_date)

            if exceeding_limit:
                return ErrorResponse('A transaction exceeding company limit exist',
                                     status=status.HTTP_400_BAD_REQUEST, code=status.HTTP_400_BAD_REQUEST)

            if is_tenor_exceeding_limit:
                return ErrorResponse('A transaction exceeding company tenor limit exist',
                                     status=status.HTTP_400_BAD_REQUEST, code=status.HTTP_400_BAD_REQUEST)

            if self.payment.cashflow_generator.status \
                in [CashFlowGenerator.Status.DRAFT, CashFlowGenerator.Status.PENDAUTH]:
                require_approval = approval_svc.is_transaction_require_approval(converted_amount=discounted_amount)
                payment_approval_svc = PaymentApprovalService(company=self.payment.company)
                can_bypass_approval = payment_approval_svc.can_bypass_approval(user=self.payment.create_user)

                if require_approval and not can_bypass_approval:
                    return ErrorResponse('A transaction required an approval',
                                        status=status.HTTP_400_BAD_REQUEST, code=status.HTTP_400_BAD_REQUEST)
        return None

    def create_ticket(self, request: Request) -> dict:
        if not self.payment.execution_timing:
            raise Exception('The execution timing has not been set.')
        if self.payment.execution_timing == Payment.ExecutionTiming.SCHEDULED:
            raise Exception(
                f'Can not perform RFQ for payment with {Payment.ExecutionTiming.SCHEDULED} timing')
        resp = self.validate_transaction_limit_and_approval()
        if resp:
            return self.construct_response(responses=MultiResponse([resp]).data)
        return self.create_ticket_with_rfq_api_view(request=request)

    def construct_error(self, error: dict) -> dict:
        return RfqErrorProvider.construct_from_rfq_error_response(error=error)

    def construct_response(self, responses: List[dict]) -> dict:
        ticket_ids = []
        ticket_data_dict = {}
        errors = []
        for response in responses:
            if response['status'] in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
                ticket_data = response['data']
                ticket_id = ticket_data['ticket_id']
                ticket_ids.append(ticket_id)
                ticket_data_dict[ticket_id] = ticket_data
                continue
            error = self.construct_error(error=response)
            errors.append(error)

        tickets = Ticket.objects.filter(ticket_id__in=ticket_ids)
        for ticket in tickets:
            ticket_data = ticket_data_dict[ticket.ticket_id]
            fee = ticket.fee if ticket.fee else 0
            spot_rate = ticket.spot_rate if ticket.spot_rate else 0
            quote_fee = ticket.quote_fee if ticket.quote_fee else 0
            ticket.pangea_fee = f"{round(fee * spot_rate, 4)} / {round(fee * 100, 2)}%"

            broker_fee_svc = BrokerFeeProvider(company=ticket.company)
            broker_fee, broker_fee_pct = broker_fee_svc.get_broker_fee_from_ticket(
                ticket=ticket)
            ticket.broker_fee = broker_fee_svc.to_fee_expression(
                fee=broker_fee, fee_pct=broker_fee_pct)

            # cosmetic fee calculation
            ticket.forward_points_str = self.generate_fwd_points_expression(
                ticket=ticket)

            for field_name in self.ADDITIONAL_FIELDS:
                setattr(ticket, field_name, ticket_data.get(field_name))

        return {
            "success": tickets,
            "failed": errors
        }

    def generate_fwd_points_expression(self, ticket: Ticket) -> str:
        if ticket.fwd_points is None or ticket.rate is None:
            return f"0.0 / 0.0%"
        fwd_points_pct = round(ticket.fwd_points / ticket.rate * 100, 2)
        return f"{round(ticket.fwd_points, 5)} / {fwd_points_pct}%"

    def create_ticket_with_rfq_api_view(self, request: Request) -> dict:
        try:
            with transaction.atomic():
                cashflows = self.get_cashflow()

                payloads = []
                for cashflow in cashflows:
                    payload = TicketPayloadProvider.get_create_ticket_rfq_api_payload(
                        payment=self.payment,
                        cashflow=cashflow
                    )
                    try:
                        existing_ticket = Ticket.objects.get(
                            cashflow_id=cashflow.cashflow_id)
                        payload['ticket_id'] = str(existing_ticket.ticket_id)
                    except Ticket.DoesNotExist as e:
                        pass
                    payloads.append(payload)

                logger.info(json.dumps(payloads))
                multiple_responses = trading_provider.rfq(
                    user=request.user, request=payloads)
                return self.construct_response(responses=multiple_responses.data)
        except Exception as e:
            raise e.with_traceback(e.__traceback__)

    def create_ticket_with_no_rfq(self) -> dict:
        try:
            with transaction.atomic():
                converter = PaymentToTicketConverter(payment=self.payment)
                tickets, errors = converter.convert_to_tickets()
                return {
                    'success': list(tickets),
                    'failed': errors
                }
        except Exception as e:
            raise e.with_traceback(e.__traceback__)


class BulkPaymentRfqService:

    @staticmethod
    def bulk_payment_rfq(request: Request, payment_ids: List[int]) -> List[dict]:
        with transaction.atomic():
            scheduled_payments_id = []
            bulk_rfq_status = []
            payments = Payment.objects.filter(id__in=payment_ids)
            for payment in payments:
                if payment.execution_timing != Payment.ExecutionTiming.IMMEDIATE:
                    scheduled_payments_id.append(str(payment.pk))
                    continue

                rfq_service = PaymentRfqService(payment=payment)
                rfq_status = rfq_service.create_ticket(request=request)
                bulk_rfq_status.append({
                    'payment_id': payment.pk,
                    'rfq_status': rfq_status
                })
            if len(scheduled_payments_id) > 0:
                raise Exception(
                    f"Scheduled payment exist in the payment id list: {','.join(scheduled_payments_id)}")
            return bulk_rfq_status
