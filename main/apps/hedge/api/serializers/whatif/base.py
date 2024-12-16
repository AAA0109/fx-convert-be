from rest_framework import serializers

from main.apps.strategy.models.choices import Strategies


class WhatIfRequestSerializer(serializers.Serializer):
    strategy = serializers.ChoiceField(choices=Strategies.choices, default=Strategies.AUTOPILOT)


class CreditUsageResponse(serializers.Serializer):
    available = serializers.DecimalField(max_digits=20, decimal_places=2)
    required = serializers.DecimalField(max_digits=20, decimal_places=2)


class RateResponse(serializers.Serializer):
    fwd_rate = serializers.DecimalField(max_digits=20, decimal_places=6)
    spot_rate = serializers.DecimalField(max_digits=20, decimal_places=6)
    fwd_points = serializers.DecimalField(max_digits=20, decimal_places=6)


class FeeResponse(serializers.Serializer):
    fee_type = serializers.CharField()
    percentage = serializers.DecimalField(max_digits=20, decimal_places=4)
    bps = serializers.DecimalField(max_digits=20, decimal_places=4)
    cost = serializers.DecimalField(max_digits=20, decimal_places=4)
