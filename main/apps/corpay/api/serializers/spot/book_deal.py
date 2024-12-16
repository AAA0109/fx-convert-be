from rest_framework import serializers


class BookDealRequestSerializer(serializers.Serializer):
    quote_id = serializers.CharField()


class BookDealResponseSerializer(serializers.Serializer):
    order_number = serializers.CharField(source='orderNumber')
    token = serializers.UUIDField()
    settlement_date = serializers.DateField(source='settlementDate', required=False)

    def to_representation(self, instance):
        return instance

    def to_internal_value(self, data):
        return data
