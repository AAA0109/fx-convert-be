from rest_framework import serializers
from main.apps.marketdata.models.fx.trading_calendar import (
    TradingCalendar
)


class TradingCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingCalendar
        fields = ('start_date', 'end_date', 'is_closed', 'pair_id')
