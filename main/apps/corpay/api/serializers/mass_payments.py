from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.corpay.api.serializers.choices import MASS_PAYMENT_METHODS
from main.apps.corpay.api.serializers.spot.rate import CurrencyAmountSerializer
from main.apps.corpay.models import Locksides
from main.apps.corpay.services.api.dataclasses.mass_payment import QuotePayment, QuotePaymentsBody


class QuotePaymentSerializer(serializers.Serializer):
    beneficiary_id = serializers.CharField()
    payment_method = serializers.ChoiceField(choices=MASS_PAYMENT_METHODS)
    amount = serializers.FloatField()
    lock_side = serializers.ChoiceField(choices=Locksides.choices)
    payment_currency = serializers.CharField()
    settlement_currency = serializers.CharField()
    settlement_method = serializers.ChoiceField(choices=MASS_PAYMENT_METHODS)
    settlement_account_id = serializers.CharField()
    payment_reference = serializers.CharField(required=False)
    purpose_of_payment = serializers.CharField()
    remitter_id = serializers.CharField(required=False)
    delivery_date = serializers.DateField(required=False)
    payment_id = serializers.CharField(required=False)

    def to_internal_value(self, data):
        return QuotePayment(
            beneficiaryId=data.get('beneficiary_id'),
            paymentMethod=data.get('payment_method'),
            amount=data.get('amount'),
            lockside=data.get('lock_side'),
            paymentCurrency=data.get('payment_currency'),
            settlementCurrency=data.get('settlement_currency'),
            settlementMethod=data.get('settlement_method'),
            settlementAccountId=data.get('settlement_account_id'),
            paymentReference=data.get('payment_reference'),
            purposeOfPayment=data.get('purpose_of_payment'),
            remitterId=data.get('remitter_id'),
            deliveryDate=data.get('delivery_date'),
            paymentId=data.get('payment_id')
        )


class QuotePaymentsRequestSerializer(serializers.Serializer):
    payments = QuotePaymentSerializer(many=True)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return QuotePaymentsBody(payments=data.get('payments'))


class PaymentSummarySerializer(serializers.Serializer):
    payment_currency = serializers.CharField(source='paymentCurrency')
    amount_total = serializers.FloatField(source='amountTotal')
    settlement_currency = serializers.CharField(source='settlementCurrency')
    settlement_amount = serializers.FloatField(source='settlementAmount')
    rate = serializers.FloatField()
    lock_side = serializers.CharField(source='lockSide')
    rate_type = serializers.CharField(source='rateType')


class PaymentTrackerSerializer(serializers.Serializer):
    payment_id = serializers.CharField(source='paymentId')
    tracker_id = serializers.CharField(source='trackerId')


class QuotePaymentsResponseSerializer(serializers.Serializer):
    expiry = serializers.IntegerField()
    payment_summary = PaymentSummarySerializer(many=True, source='paymentSummary')
    fees = CurrencyAmountSerializer(many=True)
    payment_trackers = PaymentTrackerSerializer(many=True, source='paymentTrackers')
    quote_id = serializers.CharField()
    session_id = serializers.CharField()


class BookPaymentsRequestSerializer(serializers.Serializer):
    quote_id = serializers.CharField()
    session_id = serializers.CharField()
    combine_settlements = serializers.BooleanField()


class BookPaymentsResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    order_number = serializers.IntegerField(source='orderNumber')
