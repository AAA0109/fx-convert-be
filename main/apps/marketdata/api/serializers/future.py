from rest_framework import serializers

from main.apps.ibkr.models import FutureContract
from main.apps.ibkr.models.future_contract import FutureContractIntra
from main.apps.marketdata.models.future.future_liquid_hour import FutureLiquidHours
from main.apps.marketdata.models.future.future_trading_hour import FutureTradingHours


class FutureSerializer(serializers.ModelSerializer):

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

class FutureIntraSerializer(serializers.ModelSerializer):

    class Meta:
        model = FutureContractIntra
        fields = [
            "base",
            "date",
            "rate",
            "rate_bid",
            "rate_ask"
        ]

class FutureTradingCalenderSerializer(serializers.ModelSerializer):

    class Meta:
        abstract = True
        fields = [
            "future_contract_id",
            "date",
            "start_date",
            "end_date",
            "data_cut_id",
            "is_closed"
        ]


class LiquidHoursSerializer(FutureTradingCalenderSerializer):

    class Meta:
        model = FutureLiquidHours
        fields = "__all__"


class TradingHoursSerializer(FutureTradingCalenderSerializer):

    class Meta:
        model = FutureTradingHours
        fields = "__all__"
