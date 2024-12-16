from rest_framework import serializers
from main.apps.ibkr.models import FutureContract


class FutureContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = FutureContract
        fields = [
            "base",
            "con_id",
            "currency",
            "description",
            "exchange",
            "exchanges",
            "fut_base",
            "fut_cont_size",
            "fut_month_symbol",
            "fut_month",
            "fut_start_dt",
            "fut_symbol",
            "fut_val_pt",
            "fut_year",
            "last_dt",
            "lcode_long",
            "liquid_hours",
            "local_symbol",
            "market_name",
            "min_tick",
            "multiplier",
            "price_magnifier",
            "roll_dt",
            "sec_type",
            "symbol",
            "timezone_id",
            "trading_hours"
        ]
