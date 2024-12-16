from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.currency.models.fxpair import FxPair
from main.apps.payment.api.serializers.choices import DATE_TYPES
from main.apps.oems.api.serializers.fields import CurrencyRateField


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Value date calendar request serializer',
            value={
                "pair": "USDEUR",
                "start_date": "2024-03-28",
                "end_date": "2024-04-1"
            },
        ),
    ]
)
class ValueDateCalendarRequestSerializer(serializers.Serializer):
    pair = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError("start_date must come before end_date")
        return attrs

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data['pair'] = FxPair.get_pair(pair=data['pair'])
        return data


class ValueDateSerializer(serializers.Serializer):
    date = serializers.DateField()
    date_type = serializers.ChoiceField(choices=DATE_TYPES)
    fee = CurrencyRateField(coerce_to_string=False)
    fee_unit = serializers.CharField()
    tradable = serializers.BooleanField()
    executable_time = serializers.DateTimeField(required=False, allow_null=True)


class ValueDateCalendarResponseSerializer(serializers.Serializer):
    dates = ValueDateSerializer(many=True)
