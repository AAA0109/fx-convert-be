from datetime import date, datetime
from typing import List, Optional, Union
from rest_framework import status
from rest_framework.exceptions import ValidationError, ErrorDetail

from main.apps.account.models import User
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment


class TicketPayloadProvider:

    @staticmethod
    def get_create_ticket_attributes(payment:Payment, cashflow:SingleCashFlow) -> dict:
        value_date = cashflow.pay_date.date()

        sell_currency = cashflow.sell_currency
        buy_currency = cashflow.buy_currency

        execution_strategy = payment.get_ticket_execution_strategy()
        action = Ticket.Actions.RFQ.value if payment.execution_timing == Payment.ExecutionTiming.IMMEDIATE\
                                            else Ticket.Actions.EXECUTE

        payload = {
            'action': action,
            'amount': cashflow.amount,
            'cashflow_id': cashflow.cashflow_id,
            "buy_currency": buy_currency,
            "sell_currency": sell_currency,
            'lock_side': cashflow.lock_side,
            "company": cashflow.company,
            "execution_strategy": execution_strategy,
            "value_date": value_date,
            "beneficiaries": [
                {
                    "beneficiary_id": payment.destination_account_id,
                    "method": payment.destination_account_method,
                    "purpose_of_payment": payment.purpose_of_payment
                }
            ],
            "settlement_info": [
                {
                    "settlement_account_id": payment.origin_account_id,
                    "method": payment.origin_account_method,
                    "payment_reference": cashflow.name,
                }
            ]
        }
        return payload


    @staticmethod
    def get_create_ticket_rfq_api_payload(payment:Payment, cashflow:SingleCashFlow) -> dict:

        # technically, there are RFQ execution strategies but ignore for now
        # execution_strategy = payment.get_ticket_execution_strategy()

        payload = {
            "cashflow_id": str(cashflow.cashflow_id),
            "sell_currency": cashflow.sell_currency.mnemonic,
            "buy_currency": cashflow.buy_currency.mnemonic,
            "amount": cashflow.amount,
            "lock_side": cashflow.lock_side.mnemonic,
            "value_date": str(cashflow.pay_date.date()),
            # "execution_strategy": execution_strategy,
            "beneficiaries": [
                {
                    "beneficiary_id": payment.destination_account_id,
                    "method": payment.destination_account_method,
                    "purpose_of_payment": payment.purpose_of_payment
                }
            ],
            "settlement_info": [
                {
                    "settlement_account_id": payment.origin_account_id,
                    "method": payment.origin_account_method,
                    "payment_reference": cashflow.name,
                }
            ]
        }

        if payment.execution_timing == Payment.ExecutionTiming.SCHEDULED:
            payload['tenor'] = Ticket.Tenors.SPOT

        return payload

    @staticmethod
    def get_create_ticket_execute_api_payload(payment:Payment, cashflow:SingleCashFlow, auth_user: User = None) -> dict:

        execution_strategy = payment.get_ticket_execution_strategy()

        payload = {
            "cashflow_id": str(cashflow.cashflow_id),
            "sell_currency": cashflow.sell_currency.mnemonic,
            "buy_currency": cashflow.buy_currency.mnemonic,
            "amount": cashflow.amount,
            "lock_side": cashflow.lock_side.mnemonic,
            "value_date": str(cashflow.pay_date.date()),
            "execution_strategy": execution_strategy,
            "beneficiaries": [
                {
                    "beneficiary_id": payment.destination_account_id,
                    "method": payment.destination_account_method,
                    "purpose_of_payment": payment.purpose_of_payment
                }
            ],
            "settlement_info": [
                {
                    "settlement_account_id": payment.origin_account_id,
                    "method": payment.origin_account_method,
                    "payment_reference": cashflow.name,
                }
            ]
        }

        if payment.execution_timing == Payment.ExecutionTiming.SCHEDULED:
            payload['tenor'] = Ticket.Tenors.SPOT

        if auth_user is not None:
            payload['auth_user'] = auth_user.pk

        return payload

    @staticmethod
    def get_payment_validation_payload(attrs:dict, occurrence_date:Optional[Union[datetime, date]] = None,
                                       installment:Optional[dict] = None) -> dict:

        value_date = attrs.get('delivery_date', None)
        if occurrence_date:
            value_date = occurrence_date.date() if isinstance(occurrence_date, datetime) else occurrence_date
        elif installment:
            value_date = installment.get('date', None)

        payload = {
            "sell_currency": installment.get('sell_currency', None) if installment else attrs.get('sell_currency', None),
            "buy_currency": installment.get('buy_currency', None) if installment else attrs.get('buy_currency', None),
            "amount": installment.get('amount', None) if installment else attrs.get('amount', None),
            "lock_side": installment.get('lock_side', None) if installment else attrs.get('lock_side', None),
            "value_date": str(value_date),
            "beneficiaries": [
                {
                    "beneficiary_id": attrs.get('destination_account_id', None),
                    "method": attrs.get('destination_account_method', None),
                    "purpose_of_payment": attrs.get('purpose_of_payment', None)
                }
            ],
            "settlement_info": [
                {
                    "settlement_account_id": attrs.get('origin_account_id', None),
                    "method": attrs.get('origin_account_method', None),
                    "payment_reference": attrs.get('purpose_of_payment', None)
                }
            ]
        }
        if attrs.get('execution_timing', None) == Payment.ExecutionTiming.SCHEDULED:
            payload['tenor'] = Ticket.Tenors.SPOT
        return payload

    @staticmethod
    def get_ticket_execution_payload(payment:Payment, ticket:Optional[Ticket] = None, cashflow:Optional[SingleCashFlow] = None, auth_user: User = None) -> dict:
        payload = {}
        if ticket:
            execution_strategy = payment.get_ticket_execution_strategy()
            payload = {
                'ticket_id': str(ticket.ticket_id),
                'cashflow_id': str(ticket.cashflow_id),
                'sell_currency': ticket.sell_currency.mnemonic,
                'buy_currency': ticket.buy_currency.mnemonic,
                'amount': ticket.amount,
                'lock_side': ticket.lock_side.mnemonic,
                'value_date': str(ticket.value_date),
                "execution_strategy": execution_strategy,
            }
            if auth_user is not None:
                payload['auth_user'] = auth_user.pk
            if payment.execution_timing == Payment.ExecutionTiming.SCHEDULED:
                payload['tenor'] = Ticket.Tenors.SPOT
        elif cashflow:
            payload = TicketPayloadProvider.get_create_ticket_execute_api_payload(payment=payment, cashflow=cashflow, auth_user=auth_user)

        return payload


class RfqErrorProvider:

    @staticmethod
    def generate_additional_data_dict(additional_data:dict) -> Optional[dict]:
        if not additional_data:
            return None

        additional_data_dict = {}
        for key in additional_data.keys():
            if isinstance(additional_data[key], list):
                items = []
                for item in additional_data[key]:
                    items.append(str(item))
                additional_data_dict[key] = items
                continue

            additional_data_dict[key] = additional_data[key]
        return additional_data_dict

    @staticmethod
    def construct_from_rfq_error_response(error:dict) -> dict:
        error_data:dict = error['data']
        error_code = error['status']
        detail = error_data['message']
        additional_data = RfqErrorProvider().generate_additional_data_dict(additional_data=error_data.get('data', None))
        cashflow_id = None
        ticket_id = None
        if error_code == status.HTTP_400_BAD_REQUEST:
            try:
                cashflow_id = error_data['data'].serializer.initial_data['cashflow_id']
            except:
                pass
        if error_code == status.HTTP_500_INTERNAL_SERVER_ERROR or error_code == status.HTTP_410_GONE:
            try:
                ticket_id = str(error_data['data']['ticket_id'])
            except:
                pass

        return {
            'ticket_id': ticket_id,
            'cashflow_id': cashflow_id,
            'status': error_data['status'],
            'message': detail,
            'code': error_code,
            'data': additional_data
        }

    @staticmethod
    def construct_from_ticket_validation_error(e:Union[ValidationError, Exception], cashflow:SingleCashFlow) -> dict:
        return {
            'ticket_id': None,
            'cashflow_id': cashflow.cashflow_id,
            'status': status.HTTP_400_BAD_REQUEST if isinstance(e, ValidationError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': e.args[0] if isinstance(e, ValidationError) else str(e),
            'code': e.status_code if isinstance(e, ValidationError) else status.HTTP_500_INTERNAL_SERVER_ERROR
        }

    @staticmethod
    def construct_from_execute_error_response(error:dict) -> dict:
        return RfqErrorProvider.construct_from_rfq_error_response(error=error)

    @staticmethod
    def construct_for_payment_validation(response:dict) -> List[dict]:
        data = response['data']['data']
        validation_errors = []
        for key in data:
            error_detail:ErrorDetail = data[key][0]
            validation_errors.append(
                {
                    "field": key,
                    "detail": error_detail.__str__()
                }
            )
        return validation_errors
