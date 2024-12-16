from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.currency.models.fxpair import FxPair


DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Market Spot Dates Request",
            value={
                'pairs': ['USDEUR', 'GBPJPY', 'MXNUSD']
            }
        )
    ])
class MarketSpotDateRequestSerializer(serializers.Serializer):
    pairs = serializers.ListField(child=serializers.CharField())

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        pairs = []
        for pair_str in set(data['pairs']):
            try:
                pairs.append(FxPair.get_pair(pair=pair_str))
            except:
                pass
        return pairs


class MarketSpotDateSerializer(serializers.Serializer):
    pair = serializers.CharField()
    spot_date = serializers.DateField()
    executable_time = serializers.DateTimeField()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Market Spot Dates Request",
            value={
                'spot_dates': [
                    {
                        "pair": "USDEUR",
                        "spot_date": datetime.now().date(),
                        "executable_time": datetime.now().strftime(DATE_FORMAT)
                    },
                    {
                        "pair": "GBPJPY",
                        "spot_date": (datetime.now() + timedelta(days=2))\
                            .date(),
                        "executable_time": (datetime.now() + timedelta(days=2))\
                            .strftime(DATE_FORMAT)
                    },
                    {
                        "pair": "MXNUSD",
                        "spot_date": datetime.now().date(),
                        "executable_time": datetime.now().strftime(DATE_FORMAT)
                    }
                ]
            }
        )
    ])
class MarketSpotDatesSerializer(serializers.Serializer):
    spot_dates = MarketSpotDateSerializer(many=True)
