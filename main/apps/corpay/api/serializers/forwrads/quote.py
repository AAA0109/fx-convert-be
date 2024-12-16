from rest_framework import serializers

from main.apps.corpay.api.serializers.choices import FORWARD_TYPE, RATE_OPERATION
from main.apps.corpay.models.choices import Locksides
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody
from main.apps.currency.models import Currency


class ForwardQuoteRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    buy_currency = serializers.CharField()
    forward_type = serializers.ChoiceField(
        choices=FORWARD_TYPE
    )
    lock_side = serializers.ChoiceField(
        choices=Locksides.choices
    )
    maturity_date = serializers.DateField()
    open_date_from = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="(required if 'forwardType': 'O') - Applies only to Open Forwards."
    )
    sell_currency = serializers.CharField()

    def to_representation(self, instance):
        return {
            "amount": instance.amount,
            "buy_currency": Currency.objects.get(mnemonic=instance.buy_currency),
            "forward_type": instance.forward_type,
            "lock_side": instance.lock_side,
            "maturity_date": instance.maturity_date,
            "open_date_from": instance.open_date_from,
            "sell_currency": Currency.objects.get(mnemonic=instance.sell_currency)
        }

    def to_internal_value(self, data):
        return RequestForwardQuoteBody(
            amount=data.get('amount'),
            buyCurrency=data.get('buy_currency'),
            forwardType=data.get('forward_type'),
            lockSide=data.get('lock_side'),
            maturityDate=data.get('maturity_date'),
            sellCurrency=data.get('sell_currency'),
            OpenDateFrom=data.get('open_date_from')
        )


class ForwardRateSerializer(serializers.Serializer):
    value = serializers.FloatField()
    lock_side = serializers.ChoiceField(choices=Locksides.choices, source='lockSide')
    rate_type = serializers.CharField(source='rateType')
    operation = serializers.ChoiceField(choices=RATE_OPERATION)


class ForwardAmountSerializer(serializers.Serializer):
    currency = serializers.CharField()
    amount = serializers.FloatField()


class ForwardQuoteResponseSerializer(serializers.Serializer):
    rate = ForwardRateSerializer()
    quote_id = serializers.CharField(source='quoteId')
    payment = ForwardAmountSerializer()
    settlement = ForwardAmountSerializer()
