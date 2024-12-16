from rest_framework import serializers

from main.apps.payment.api.serializers.payment import FailedPaymentRfqSerializer
from main.apps.oems.api.serializers.fields import CurrencyAmountField, CurrencyRateField


class PaymentExecutionSuccessSerializer(serializers.Serializer):
    ticket_id = serializers.CharField()
    status = serializers.CharField(required=False)
    action = serializers.CharField()
    spot_rate = CurrencyRateField(coerce_to_string=False, required=False)
    fwd_points = CurrencyRateField(coerce_to_string=False, required=False)
    all_in_rate = CurrencyRateField(coerce_to_string=False, required=False)
    value_date = serializers.DateField()
    delivery_fee = CurrencyRateField(coerce_to_string=False, required=False)
    payment_amount = CurrencyAmountField(coerce_to_string=False, required=False)
    total_cost = CurrencyAmountField(coerce_to_string=False, required=False)


class PaymentExecutionErrorSerializer(FailedPaymentRfqSerializer):
    pass


class PaymentExecutionResponseSerializer(serializers.Serializer):
    success = PaymentExecutionSuccessSerializer(many=True)
    error = PaymentExecutionErrorSerializer(many=True)
