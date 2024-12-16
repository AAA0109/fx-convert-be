from rest_framework import serializers


class ForwardBookQuoteRequestSerializer(serializers.Serializer):
    quote_id = serializers.CharField()


class ForwardBookQuoteResponseSerializer(serializers.Serializer):
    order_number = serializers.CharField(source="orderNumber")
    token = serializers.CharField()
    forward_id = serializers.IntegerField(source="forwardId")
