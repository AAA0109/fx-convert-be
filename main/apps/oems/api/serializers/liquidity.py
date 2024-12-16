from rest_framework import serializers

from main.apps.currency.models.currency import Currency


class LiquidityInsightRequestSerializer(serializers.Serializer):
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)


class LiquidityDetailSerializer(serializers.Serializer):
    liquidity_status = serializers.CharField(allow_null=True)
    time = serializers.DateTimeField()
    market_status = serializers.CharField()
    spread_in_bps = serializers.FloatField(required=False, allow_null=True)


class LiquidityInsightResponseSerializer(serializers.Serializer):
    market = serializers.CharField()
    insight_data = LiquidityDetailSerializer(many=True)
    recommended_execution = LiquidityDetailSerializer(required=False, allow_null=True)


class MarketLiquidityResponse(serializers.Serializer):
    data = LiquidityInsightResponseSerializer(many=True)


class MarketLiquidityInsight(LiquidityInsightResponseSerializer):
    recommended_execution = None
    is_ndf = serializers.BooleanField(allow_null=True)
    fwd_rfq_type = serializers.CharField(allow_null=True)


class MarketsLiquidityResponse(serializers.Serializer):
    data = MarketLiquidityInsight(many=True)
