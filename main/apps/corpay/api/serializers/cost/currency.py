from rest_framework import serializers


class CostRequestSerializer(serializers.Serializer):
    aum = serializers.FloatField()


class CostTransactionSerializer(serializers.Serializer):
    transaction_low = serializers.FloatField()
    transaction_high = serializers.FloatField()
    p10 = serializers.FloatField()
    other = serializers.FloatField()
    wire = serializers.CharField()


class CostAumSerializer(serializers.Serializer):
    annualized_rate = serializers.FloatField()
    minimum_rate = serializers.FloatField()


class CostResponseSerializer(serializers.Serializer):
    transactions = CostTransactionSerializer(many=True)
    aum = CostAumSerializer()
