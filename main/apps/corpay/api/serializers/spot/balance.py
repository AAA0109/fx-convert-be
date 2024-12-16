from rest_framework import serializers

from main.apps.corpay.api.serializers.choices import BALANCE_TYPE_FROM, BALANCE_TYPE_TO


class CustomCurrencyField(serializers.Field):
    def to_representation(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return value

    def to_internal_value(self, data):
        if isinstance(data, int):
            return data
        if isinstance(data, str) and data.isdigit():
            return int(data)
        elif isinstance(data, str) and len(data) == 3:
            return data
        raise serializers.ValidationError(
            'Currency field should be an integer id or 3 mnemonic string')


class BalanceSerializer(serializers.Serializer):
    type = serializers.ChoiceField(required=True, choices=BALANCE_TYPE_TO)
    id = serializers.CharField(required=True)


class BalanceFromSerializer(BalanceSerializer):
    type = serializers.ChoiceField(choices=BALANCE_TYPE_FROM)


class CalculateBalanceRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField(required=True)
    currency = CustomCurrencyField(required=True)
    from_balance = BalanceFromSerializer(required=True)
    to_balance = BalanceSerializer(required=True)


class CalculateBalanceResponseSerializer(serializers.Serializer):
    from_value = serializers.FloatField()
    to_value = serializers.FloatField()
