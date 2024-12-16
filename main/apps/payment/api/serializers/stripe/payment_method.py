from rest_framework import serializers


class StripePaymentMethodRequestSerializer(serializers.Serializer):
    payment_method_id = serializers.CharField()


class StripePaymentMethodResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    last4 = serializers.IntegerField()
    brand = serializers.CharField()
