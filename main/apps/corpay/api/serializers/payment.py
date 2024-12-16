from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.corpay.api.serializers.mass_payments import QuotePaymentSerializer, QuotePaymentsResponseSerializer
from main.apps.corpay.api.serializers.spot.rate import SpotRateResponseRate, CurrencyAmountSerializer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Rate Request',
            value={
                'beneficiary_id': '610268780000011003',
                'payment_method': 'StoredValue',
                'amount': 100,
                'lock_side': 'Payment',
                'payment_currency': 'EUR',
                'settlement_currency': 'USD',
                'settlement_method': 'StoredValue',
                'settlement_account_id': '610268780002011002',
                'purpose_of_payment': 'PURCHASE OF GOOD(S)'
            },
        ),
    ]
)
class QuotePaymentSerializer(QuotePaymentSerializer):
    ...


class BookPaymentRequestSerializer(serializers.Serializer):
    quote_id = serializers.CharField()
    session_id = serializers.CharField()


class BookPaymentOrderResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    order_number = serializers.IntegerField(source='orderNumber')


class QuotePaymentResponseSerializer(serializers.Serializer):
    rate = SpotRateResponseRate()
    payment = CurrencyAmountSerializer()
    settlement = CurrencyAmountSerializer()
    quote = QuotePaymentsResponseSerializer()
