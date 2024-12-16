from rest_framework import serializers
from main.apps.marketdata.models.fx.rate import (
    FxForward
)


class FxForwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxForward
        fields = ("date", "pair", "tenor", "rate", "rate_bid", "rate_ask", "fwd_points", "fwd_points_ask", "depo_base",
                  "depo_quote")
