from datetime import date
from typing import List, Optional
from rest_framework import serializers, status

from main.apps.account.models.user import User
from main.apps.currency.models.currency import Currency
from main.apps.oems.services.trading import trading_provider
from main.apps.payment.services.recurrence_provider import RecurrenceProvider
from main.apps.payment.services.ticket_payload import RfqErrorProvider, TicketPayloadProvider


class PaymentValidator:
    attrs:dict
    is_installment:bool
    is_recurrence:bool
    keys:List[str]
    occurrences:List[date]
    required_fields:List[str] = ['amount', 'buy_currency', 'lock_side', 'sell_currency']
    user:User

    def __init__(self, attrs:dict, user:Optional[User] = None) -> None:
        self.keys = attrs.keys()
        self.attrs = attrs
        self.is_recurrence = self.check_recurrence()
        self.is_installment = self.check_installment()
        if self.is_recurrence:
            sell_currency = attrs['sell_currency'] if isinstance(attrs['sell_currency'], Currency) else \
                Currency.get_currency(currency=attrs['sell_currency'])
            buy_currency = attrs['buy_currency'] if isinstance(attrs['buy_currency'], Currency) else \
                Currency.get_currency(currency=attrs['buy_currency'])
            recurrence_provider = RecurrenceProvider(periodicity=self.attrs['periodicity'],
                                                        periodicity_start_date=self.attrs['periodicity_start_date'],
                                                        periodicity_end_date=self.attrs['periodicity_end_date'])
            self.occurrences = recurrence_provider.get_occurrence_dates(sell_currency=sell_currency,
                                                                        buy_currency=buy_currency)
        self.user = user

    def validate_payload(self) -> dict:
        # Validate if FE post installment item and set periodicity at the same time
        if self.is_installment and self.is_recurrence:
            raise serializers.ValidationError({
                'periodicity and installments': 'Payment can only be recurrence or installments'
            })

        if not self.is_installment:
            for key in self.required_fields:
                if key == 'amount' and key in self.keys and self.attrs[key] < 1:
                    raise serializers.ValidationError({
                        key: f'{key} value must be >= 1'
                    })

                if key not in self.keys:
                    raise serializers.ValidationError({
                        key: f'{key} is required'
                    })

        self.validate_for_ticket()

        return self.attrs

    def check_recurrence(self) -> bool:
        periodicity = self.attrs.get('periodicity', None)
        return True if periodicity else False

    def check_installment(self) -> bool:
        installments = self.attrs.get('installments', None)
        return True if installments else False

    def get_recurrence_payloads(self) -> List[dict]:
        payloads = []
        for occurrence in self.occurrences:
            payloads.append(TicketPayloadProvider().get_payment_validation_payload(attrs=self.attrs, occurrence_date=occurrence))
        return payloads

    def get_installments_payloads(self) -> List[dict]:
        payloads = []
        for installment in self.attrs['installments']:
            payloads.append(TicketPayloadProvider().get_payment_validation_payload(attrs=self.attrs, installment=installment))
        return payloads

    def get_on_time_payloads(self) -> List[dict]:
        payloads = []
        payloads.append(TicketPayloadProvider().get_payment_validation_payload(attrs=self.attrs))
        return payloads

    def validate_for_ticket(self) -> None:
        payloads = None
        validation_errors = []
        if self.is_recurrence:
            payloads = self.get_recurrence_payloads()
        elif self.is_installment:
            payloads = self.get_installments_payloads()
        elif not self.is_recurrence and not self.is_installment:
            payloads = self.get_on_time_payloads()

        responses = trading_provider.validate(user=self.user, request=payloads, basic=True)

        error_found = False
        for response in responses.data:
            if response['status'] == status.HTTP_400_BAD_REQUEST:
                error_found = True
                validation_errors += RfqErrorProvider().construct_for_payment_validation(response=response)

        if error_found:
            raise serializers.ValidationError(validation_errors)
