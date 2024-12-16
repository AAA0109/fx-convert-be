from rest_framework import serializers


class ForwardCompleteOrderRequestSerializer(serializers.Serializer):
    forward_id = serializers.IntegerField()
    settlement_account = serializers.CharField()
    forward_reference = serializers.CharField(required=False)


class ForwardCompleteOrderResponseSerializer(serializers.Serializer):
    forward_id = serializers.IntegerField(source='forwardId')
    order_number = serializers.CharField(source='orderNumber')
