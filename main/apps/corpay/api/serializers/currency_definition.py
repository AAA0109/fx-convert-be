from rest_framework import serializers

from main.apps.corpay.models import CurrencyDefinition
from main.apps.currency.api.serializers.models.currency import CurrencySerializer


class CurrencyDefinitionSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer()
    class Meta:
        model = CurrencyDefinition
        fields = [
            'currency',
            'p10',
            'wallet',
            'wallet_api',
            'ndf',
            'fwd_delivery_buying',
            'fwd_delivery_selling',
            'incoming_payments',
            'outgoing_payments'
        ]

