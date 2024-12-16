from rest_framework import serializers

from main.apps.hedge.api.serializers.whatif.base import CreditUsageResponse, RateResponse, FeeResponse


class ParachuteHedgeMetricResponse(serializers.Serializer):
    potential_loss_mitigated = serializers.FloatField()
    return_risk_ratio = serializers.FloatField(required=False, allow_null=True)
    hedge_efficiency_ratio = serializers.FloatField()


class ParachuteWhatIfResponseSerializer(serializers.Serializer):
    credit_usage = CreditUsageResponse(read_only=True)
    rate = RateResponse(read_only=True)
    fee = serializers.ListSerializer(child=FeeResponse(read_only=True))
    hedge_metric = ParachuteHedgeMetricResponse(read_only=True)
