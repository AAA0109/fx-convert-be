import logging
from datetime import datetime
from typing import List, Optional, Tuple
import uuid

from django.db import transaction

from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.currency.models.currency import Currency
from main.apps.marketdata.services.initial_marketdata import convert_currency_amount
from main.apps.oems.models import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.delete_payment_action import DeletePaymentAction
from main.apps.payment.services.execution_time_assigner import PaymentExecutionTimeAssigner
from main.apps.payment.services.transaction_date import PaymentTransactionDateService

logger = logging.getLogger(__name__)

class PaymentService:
    cashflow_modified_fields = {
        'amount': 'amount',
        'buy_currency': 'buy_currency',
        'delivery_date': 'value_date',
        'lock_side': 'lock_side',
        'sell_currency': 'sell_currency'
    }

    payment_modified_fields = {
        'destination_account_id': 'destination_account_id',
        'destination_account_method': 'destination_account_method',
        'execution_timing': 'execution_timing',
        'origin_account_id': 'origin_account_id',
        'origin_account_method': 'origin_account_method',
        'purpose_of_payment': 'purpose_of_payment'
    }

    def __init__(self) -> None:
        pass

    @staticmethod
    def create_payment(
        company: Company,
        name: str,
        # with default argument
        origin_account_id: str = None,
        origin_account_method: str = None,
        destination_account_id: str = None,
        destination_account_method: str = None,
        amount: float = 0,
        cntr_amount: float = 0,
        buy_currency: str = None,
        delivery_date: datetime = None,
        execution_timing: str = None,
        fee_in_bps: int = 0,
        fee: float = 0,
        installments: List[dict] = None,
        lock_side: str = None,
        periodicity_end_date: datetime.date = None,
        periodicity_start_date: datetime.date = None,
        periodicity: str = None,
        purpose_of_payment: str = None,
        sell_currency: str = None,
        payment_status=Payment.PaymentStatus.DRAFTING,
        payment_ident: str = None,
        payment_group: str = None,
        create_user: User = None,
        auth_user: User = None,
    ) -> Payment:

        with transaction.atomic():
            buy_currency = Currency.get_currency(currency=buy_currency) if buy_currency else None
            sell_currency = Currency.get_currency(currency=sell_currency) if sell_currency else None
            lock_side_currency = Currency.get_currency(currency=lock_side) if lock_side else None

            is_installment = installments != None and len(installments) > 0
            is_recurring = periodicity is not None

            generator = CashFlowGenerator(
                amount=amount,
                cntr_amount=cntr_amount,
                buy_currency=buy_currency,
                company=company,
                installment=is_installment,
                lock_side=lock_side_currency,
                name=name,
                periodicity_end_date=periodicity_end_date,
                periodicity_start_date=periodicity_start_date,
                periodicity=periodicity,
                recurring=is_recurring,
                sell_currency=sell_currency,
                value_date=delivery_date
            )
            generator.save()

            payment = Payment(
                cashflow_generator=generator,
                destination_account_id=destination_account_id,
                destination_account_method=destination_account_method,
                execution_timing=Payment().get_exec_timing_from_exec_option(exec_option=execution_timing),
                execution_option=execution_timing,
                fee_in_bps=fee_in_bps,
                fee=fee,
                origin_account_id=origin_account_id,
                origin_account_method=origin_account_method,
                purpose_of_payment=purpose_of_payment,
                payment_status=payment_status,
                payment_ident=payment_ident,
                payment_group=payment_group,
                create_user=create_user,
                auth_user=auth_user,
                company=company,
            )
            payment.save()

            payment.cashflow_generator.generate_cashflows(installments=installments)

            return payment

    @staticmethod
    def update_payment(
        payment: Payment,
        company: Company,
        destination_account_id: str,
        name: str,
        origin_account_id: str,
        # with default argument
        destination_account_method: str = None,
        origin_account_method: str = None,
        amount: float = 0,
        cntr_amount: float = 0,
        buy_currency: str = None,
        delivery_date: datetime = None,
        execution_timing: str = None,
        fee_in_bps: int = 0,
        fee: float = 0,
        installments: List[dict] = None,
        lock_side: str = None,
        periodicity_end_date: datetime.date = None,
        periodicity_start_date: datetime.date = None,
        periodicity: str = None,
        purpose_of_payment: str = None,
        sell_currency: str = None,
        **kwargs
    ) -> Payment:
        create_new_ticket = PaymentService.should_create_new_ticket(
            payment,
            amount=amount,
            buy_currency=buy_currency,
            delivery_date=delivery_date,
            destination_account_id=destination_account_id,
            destination_account_method=destination_account_method,
            execution_timing=Payment().get_exec_timing_from_exec_option(exec_option=execution_timing),
            lock_side=lock_side,
            sell_currency=sell_currency,
            origin_account_id=origin_account_id,
            origin_account_method=origin_account_method,
            purpose_of_payment=purpose_of_payment
        )

        with transaction.atomic():
            buy_currency = Currency.get_currency(currency=buy_currency) if buy_currency else None
            sell_currency = Currency.get_currency(currency=sell_currency) if sell_currency else None
            lock_side_currency = Currency.get_currency(currency=lock_side) if lock_side else None

            cashflow = payment.cashflow_generator

            recreate_recurrence_cashflows = PaymentService().should_recreate_cashflows(cashflow=cashflow,
                                                                                       periodicity=periodicity)

            # Remove existing cashflows if updated periodicity value is different
            if recreate_recurrence_cashflows:
                single_cashflows = SingleCashFlow.objects.filter(generator=payment.cashflow_generator)
                PaymentService().unlink_cashflow_ticket(
                    cashflow_ids=[
                        str(cid) for cid in single_cashflows.values_list('cashflow_id', flat=True)
                    ]
                )
                single_cashflows.delete()

            is_installment = installments != None and len(installments) > 0
            is_recurring = periodicity is not None

            # Remove existing cashflow if user change payment type from one time to recurrence or installment
            if cashflow.recurring != is_recurring or cashflow.installment != is_installment:
                single_cashflows = SingleCashFlow.objects.filter(generator=payment.cashflow_generator)
                PaymentService().unlink_cashflow_ticket(
                    cashflow_ids=[
                        str(cid) for cid in single_cashflows.values_list('cashflow_id', flat=True)
                    ]
                )
                single_cashflows.delete()
                recreate_recurrence_cashflows = True

            cashflow.amount = amount
            cashflow.cntr_amount = cntr_amount
            cashflow.buy_currency = buy_currency
            cashflow.company = company
            cashflow.installment = is_installment
            cashflow.lock_side = lock_side_currency
            cashflow.name = name
            cashflow.periodicity = periodicity
            cashflow.periodicity_end_date = periodicity_end_date
            cashflow.periodicity_start_date = periodicity_start_date
            cashflow.recurring = is_recurring
            cashflow.sell_currency = sell_currency
            cashflow.value_date = delivery_date
            if create_new_ticket:
                PaymentService.reset_cashflows_and_tickets(cashflow)
            cashflow.save()

            payment.destination_account_id = destination_account_id
            payment.destination_account_method = destination_account_method
            payment.execution_timing = Payment().get_exec_timing_from_exec_option(exec_option=execution_timing)
            payment.execution_option = execution_timing
            payment.fee_in_bps = fee_in_bps
            payment.fee = fee
            payment.origin_account_id = origin_account_id
            payment.origin_account_method = origin_account_method
            payment.purpose_of_payment = purpose_of_payment
            payment.save()

            cashflows = payment.cashflow_generator.update_cashflows(installments=installments,
                                                        recreate_recurrence=recreate_recurrence_cashflows)

            if is_installment:
                single_cashflows = SingleCashFlow.objects.filter(generator=payment.cashflow_generator)\
                    .exclude(cashflow_id__in=[cf.cashflow_id for cf in cashflows])
                PaymentService().unlink_cashflow_ticket(
                    cashflow_ids=[
                        str(cid) for cid in single_cashflows.values_list('cashflow_id', flat=True)
                    ]
                )
                single_cashflows.delete()

            PaymentService().set_populate_transaction_date(payment=payment)

            return payment

    @staticmethod
    def delete_payment(payment: Payment) -> Optional[Payment]:
        canceled_payment = None
        delete_payment_act = DeletePaymentAction(payment=payment)
        resp = delete_payment_act.cancel_ticket()

        if resp:
            if len(resp['failed']) > 0:
                raise Exception(resp)

        with transaction.atomic():
            if payment.payment_status == Payment.PaymentStatus.DRAFTING:
                SingleCashFlow.objects.filter(generator=payment.cashflow_generator).delete()
                payment.cashflow_generator.delete()
            else:
                payment.cashflow_generator.status = CashFlowGenerator.Status.CANCELED
                payment.cashflow_generator.save()
                payment.payment_status = Payment.PaymentStatus.CANCELED
                payment.save()
                canceled_payment = payment
        return canceled_payment

    @staticmethod
    def should_recreate_cashflows(
        cashflow: CashFlowGenerator,
        periodicity: str
    ) -> bool:
        return cashflow.recurring and str(cashflow.periodicity) != periodicity

    @staticmethod
    def should_create_new_ticket(payment: Payment, **kwargs) -> bool:
        # Get the cashflow object
        cashflow = payment.cashflow_generator

        # Check cashflow modified fields
        for param_name, attr_name in PaymentService.cashflow_modified_fields.items():
            existing_value = getattr(cashflow, attr_name)
            new_value = kwargs.get(param_name)
            existing_value, new_value = PaymentService.equalize_var_value(
                existing_value=existing_value, new_value=new_value)
            if existing_value != new_value:
                return True

        # Check payment modified fields
        for param_name, attr_name in PaymentService.payment_modified_fields.items():
            existing_value = getattr(payment, attr_name)
            new_value = kwargs.get(param_name)
            existing_value, new_value = PaymentService.equalize_var_value(
                existing_value=existing_value, new_value=new_value)
            if existing_value != new_value:
                return True

        return False

    @staticmethod
    def reset_cashflows_and_tickets(cashflow: CashFlowGenerator):
        # Set ticket_id to None on the related cashflows
        cashflow.cashflows.update(ticket_id=None)

        # Set cashflow_id to None on the related tickets
        cashflow_ids = cashflow.cashflows.values_list('cashflow_id', flat=True)
        cashflow_ids_str = [str(cashflow_id) for cashflow_id in cashflow_ids]
        Ticket.objects.filter(cashflow_id__in=cashflow_ids_str).update(cashflow_id=None)

    @staticmethod
    def unlink_cashflow_ticket(cashflow_ids:List[str]):
        Ticket.objects.filter(cashflow_id__in=cashflow_ids).update(cashflow_id=None)

    @staticmethod
    def set_populate_transaction_date(payment:Payment) -> None:
        if payment.execution_timing and \
                payment.execution_timing != Payment.ExecutionTiming.IMMEDIATE:
            transaction_date_svc = PaymentTransactionDateService(payment=payment)
            transaction_date_svc.populate_transaction_dates()
        elif payment.execution_timing == Payment.ExecutionTiming.IMMEDIATE:
            SingleCashFlow.objects.filter(generator=payment.cashflow_generator)\
                .update(transaction_date=None)

    @staticmethod
    def equalize_var_value(existing_value:any, new_value:any) -> Tuple[str, str]:
        if type(existing_value) != type(new_value) and \
             (isinstance(existing_value, Currency) or isinstance(new_value, Currency)):
            existing_value = existing_value.mnemonic \
                if isinstance(existing_value, Currency) else existing_value
            new_value = new_value.mnemonic \
                if isinstance(new_value, Currency) else new_value
        return existing_value, new_value

class BulkPaymentService:
    fx_balance_accounts:List[str]
    settlement_accounts:List[dict]
    beneficiary_accounts:List[dict]
    company:Company
    user:User
    validated_data:List[dict]
    is_update:bool

    def __init__(self, company:Company, user:User, validated_data:List[dict], is_update:bool = False) -> None:
        self.company = company
        self.user = user
        self.validated_data = validated_data
        self.is_update = is_update

    def bulk_create_payments(self) -> Tuple[List[Payment], List[dict]]:
        with transaction.atomic():
            payments = []
            currency_amount_netting = []
            bulk_group = self.__generate_group_identifier()
            for valid_payment_data in self.validated_data:
                valid_payment_data = self.__append_additional_fields(
                    valid_payment_data=valid_payment_data,
                    bulk_group=bulk_group
                )
                currency_amount_netting = self.__update_currency_netting(
                    currency_netting=currency_amount_netting,
                    buy_currency=valid_payment_data['buy_currency'],
                    cntr_amount=valid_payment_data['cntr_amount']
                )
                new_payment = PaymentService.create_payment(company=self.company, **valid_payment_data)
                payments.append(new_payment)
            execution_timing_assigner = PaymentExecutionTimeAssigner(payments=payments)
            payments = execution_timing_assigner.assign_execution_time()
            return payments, currency_amount_netting

    def bulk_update_payments(self) -> Tuple[List[Payment], List[dict]]:
        with transaction.atomic():
            bulk_group = self.validated_data['payment_group']
            payments = []
            currency_amount_netting = []

            if len(self.validated_data['deleted_payments']) > 0:
                payments_to_delete = Payment.objects.filter(
                    payment_id__in=self.validated_data['deleted_payments'])
                for payment in payments_to_delete:
                    PaymentService().delete_payment(payment=payment)

            # Add additional record to bulk payment group
            for valid_payment_data in self.validated_data['added_payments']:
                valid_payment_data = self.__append_additional_fields(
                    valid_payment_data=valid_payment_data,
                    bulk_group=bulk_group
                )
                currency_amount_netting = self.__update_currency_netting(
                    currency_netting=currency_amount_netting,
                    buy_currency=valid_payment_data['buy_currency'],
                    cntr_amount=valid_payment_data['cntr_amount']
                )
                new_payment = PaymentService.create_payment(company=self.company, **valid_payment_data)
                payments.append(new_payment)

            # Update payment on bulk payment group
            for valid_payment_data in self.validated_data['updated_payments']:
                try:
                    payment = Payment.objects.get(payment_id=valid_payment_data['id'])
                    valid_payment_data = self.__append_additional_fields(
                        valid_payment_data=valid_payment_data,
                        bulk_group=bulk_group,
                        update=True
                    )
                    currency_amount_netting = self.__update_currency_netting(
                        currency_netting=currency_amount_netting,
                        buy_currency=valid_payment_data['buy_currency'],
                        cntr_amount=valid_payment_data['cntr_amount']
                    )
                    new_payment = PaymentService.update_payment(payment=payment, company=self.company, **valid_payment_data)
                    payments.append(new_payment)
                except Payment.DoesNotExist:
                    logger.error(f"Unable to update bulk payment id: {valid_payment_data['id']}")

            execution_timing_assigner = PaymentExecutionTimeAssigner(payments=payments)
            updated_payments = execution_timing_assigner.assign_execution_time()
            payments = list(Payment.objects.filter(payment_group=bulk_group))
            return payments, currency_amount_netting

    def __append_additional_fields(self, valid_payment_data:dict, bulk_group:str, update:bool = False) -> dict:
        cntr_amount = self.__get_cntr_amount(validated_data=valid_payment_data)
        valid_payment_data['cntr_amount'] = cntr_amount
        if not update:
            valid_payment_data['payment_group'] = bulk_group
            valid_payment_data['create_user'] = self.user
        return valid_payment_data

    def __update_currency_netting(self, currency_netting:List[dict], buy_currency:Currency, cntr_amount:float) -> List[dict]:
        item_index = next((index for (index, d) in enumerate(currency_netting) if d["buy_currency"] == buy_currency), None)
        if item_index is None:
            currency_netting.append({
                'buy_currency': buy_currency,
                'sum_amount': cntr_amount
            })
            return currency_netting

        currency_netting[item_index]['sum_amount'] += cntr_amount
        return currency_netting

    def __get_cntr_amount(self, validated_data:dict) -> float:
        # Current cntr amount method only work for Tenor.SPOT value date
        cntr_amount = convert_currency_amount(
            desired_currency=validated_data['buy_currency'],
            buy_currency=validated_data['buy_currency'],
            sell_currency=validated_data['sell_currency'],
            lock_side=validated_data['lock_side'],
            amount=validated_data['amount']
        )
        return cntr_amount

    def __generate_group_identifier(self) -> str:
        timestamp = int(datetime.now().timestamp())
        unique_id = uuid.uuid4()
        return f'{timestamp}_{unique_id}'
