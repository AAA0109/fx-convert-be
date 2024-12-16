from rest_framework import serializers

from main.apps.hedge.api.serializers.whatif.base import CreditUsageResponse, RateResponse, FeeResponse


class CreditUtilizationResponse(serializers.Serializer):
    credit_limit = serializers.DecimalField(max_digits=20, decimal_places=2)
    credit_used = serializers.DecimalField(max_digits=20, decimal_places=2)
    pnl = serializers.DecimalField(max_digits=20, decimal_places=2)


class AutopilotHedgeMetricResponse(serializers.Serializer):
    potential_loss_mitigated = serializers.FloatField()
    upside_preservation = serializers.FloatField()
    hedge_efficiency_ratio = serializers.FloatField(required=False, allow_null=True)


class AutopilotMarginAndFeeRequest(serializers.Serializer):
    """
    Autopilot margin and fee request object.
    """
    draft_fx_forward_id = serializers.IntegerField(required=True)


class AutopilotWhatIfResponseSerializer(serializers.Serializer):
    credit_usage = CreditUsageResponse(read_only=True)
    rate = RateResponse(read_only=True)
    fee = serializers.ListSerializer(child=FeeResponse(read_only=True))
    hedge_metric = AutopilotHedgeMetricResponse(read_only=True)


class AutopilotMarginHealthResponse(serializers.Serializer):
    credit_usage = CreditUtilizationResponse(read_only=True)
    margin_call_at = serializers.DecimalField(max_digits=20, decimal_places=2)
