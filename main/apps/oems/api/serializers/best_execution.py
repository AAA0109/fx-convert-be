from rest_framework import serializers


class BestExecutionStatusSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    market = serializers.CharField()
    recommend = serializers.BooleanField(required=False)
    session = serializers.CharField(required=False)
    check_back = serializers.DateTimeField(required=False)
    execute_before = serializers.DateTimeField(required=False)
    unsupported = serializers.BooleanField(required=False)


class LiquidityInsightSerializer(serializers.Serializer):
    liquidity = serializers.CharField()


class BestExecutionDataSerializer(serializers.Serializer):
    liquidity_insight = LiquidityInsightSerializer()
    spot_value_date = serializers.DateField()


class BestExecutionTimingSerializer(serializers.Serializer):
    execution_timings = BestExecutionStatusSerializer(many=True)
    execution_data = BestExecutionDataSerializer(required=False)
