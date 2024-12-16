from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.corpay.api.serializers.choices import MASS_PAYMENT_METHODS
from main.apps.corpay.models.choices import Locksides
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody
from main.apps.currency.models import Currency


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Rate Request',
            value={
                'payment_currency': 'USD',
                'settlement_currency': 'CAD',
                'amount': 10000,
                'lock_side': 'payment'
            },
        ),
    ]
)
class SpotRateRequestSerializer(serializers.Serializer):
    payment_currency = serializers.CharField()
    settlement_currency = serializers.CharField()
    amount = serializers.FloatField()
    lock_side = serializers.ChoiceField(choices=Locksides.choices)

    def to_representation(self, instance):
        return {
            'payment_currency': Currency.objects.get(mnemonic=instance.paymentCurrency),
            'settlement_currency': Currency.objects.get(mnemonic=instance.settlementCurrency),
            'amount': instance.amount,
            'lock_side': instance.lockSide
        }

    def to_internal_value(self, data):
        return SpotRateBody(
            paymentCurrency=data['payment_currency'],
            settlementCurrency=data['settlement_currency'],
            amount=data['amount'],
            lockSide=data['lock_side']
        )


class SpotRateResponseRate(serializers.Serializer):
    value = serializers.FloatField()
    lock_side = serializers.ChoiceField(choices=Locksides.choices, source='lockSide')
    rate_type = serializers.CharField(source='rateType')
    operation = serializers.CharField()


class CurrencyAmountSerializer(serializers.Serializer):
    currency = serializers.CharField()
    amount = serializers.FloatField()
    amount_domestic = serializers.FloatField(required=False)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Rate Response',
            value={
                "rate": {
                    "value": 1.36399,
                    "lock_side": "Payment",
                    "rate_type": "USDCAD",
                    "operation": "Multiply"
                },
                "quoteId": "d8fd5077901a48e68487be1763363c30",
                "payment": {
                    "currency": "USD",
                    "amount": 10000
                },
                "settlement": {
                    "currency": "CAD",
                    "amount": 13639.9
                },
                "cost_in_bps": 25
            },
        ),
    ]
)
class SpotRateResponseSerializer(serializers.Serializer):
    rate = SpotRateResponseRate()
    quote_id = serializers.CharField(source='quoteId')
    payment = CurrencyAmountSerializer()
    settlement = CurrencyAmountSerializer()
    cost_in_bps = serializers.IntegerField()
