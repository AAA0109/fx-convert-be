from datetime import datetime
from typing import Optional

from django.db import transaction

from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.currency.models.currency import Currency
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.transaction_date import CashflowTransactionDateService


class PaymentCashflowService:

    @staticmethod
    def create_cashflow(
        amount: float,
        cntr_amount: float,
        buy_currency: Currency,
        lock_side: Currency,
        pay_date: datetime.date,
        payment: Payment,
        sell_currency: Currency
    ) -> SingleCashFlow:
        with transaction.atomic():
            cashflow = SingleCashFlow(
                amount=amount,
                cntr_amount=cntr_amount,
                buy_currency=buy_currency,
                company=payment.cashflow_generator.company,
                description=payment.cashflow_generator.description,
                name=payment.cashflow_generator.name,
                pay_date=pay_date,
                sell_currency=sell_currency,
                status=SingleCashFlow.Status.DRAFT,
                generator=payment.cashflow_generator,
                lock_side=lock_side
            )
            cashflow.save()
            PaymentCashflowService().set_transaction_date(cashflow=cashflow)
            return cashflow

    @staticmethod
    def update_cashflow(
        amount: float,
        cntr_amount: float,
        buy_currency: Currency,
        cashflow: SingleCashFlow,
        lock_side: Currency,
        pay_date: datetime.date,
        sell_currency: Currency
    ) -> SingleCashFlow:
        with transaction.atomic():
            cashflow.amount = amount
            cashflow.cntr_amount = cntr_amount
            cashflow.buy_currency = buy_currency
            cashflow.pay_date = pay_date
            cashflow.sell_currency = sell_currency
            cashflow.lock_side = lock_side
            cashflow.ticket_id = None
            cashflow.save()
            PaymentCashflowService().remove_ticket_relation(cashflow=cashflow)
            PaymentCashflowService().set_transaction_date(cashflow=cashflow)
            return cashflow

    @staticmethod
    def delete_cashflow(payment: Payment, cashflow: SingleCashFlow) -> Optional[SingleCashFlow]:
        canceled_installment = None
        with transaction.atomic():
            if payment.payment_status == Payment.PaymentStatus.DRAFTING:
                cashflow.delete()
            else:
                cashflow.status = SingleCashFlow.Status.CANCELED
                cashflow.save()
                canceled_installment = cashflow
        return canceled_installment

    @staticmethod
    def remove_ticket_relation(cashflow:SingleCashFlow) -> None:
        Ticket.objects.filter(cashflow_id=cashflow.cashflow_id).update(cashflow_id=None)

    @staticmethod
    def set_transaction_date(cashflow:SingleCashFlow) -> None:
        payment = Payment.objects.get(cashflow_generator=cashflow.generator)
        if payment.execution_timing and \
            payment.execution_timing != Payment.ExecutionTiming.IMMEDIATE:
            transaction_date_svc = CashflowTransactionDateService(cashflow=cashflow)
            transaction_date_svc.set_transaction_date()
        elif payment.execution_timing == Payment.ExecutionTiming.IMMEDIATE:
            cashflow.transaction_date = None
            cashflow.save()
