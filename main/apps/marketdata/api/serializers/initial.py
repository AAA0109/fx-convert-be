from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

from django.db import models

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers
from main.apps.broker.models.broker import Broker

from main.apps.core.constants import VALUE_DATE_HELP_TEXT, CURRENCY_HELP_TEXT
from main.apps.currency.models.currency import Currency
from main.apps.oems.api.serializers.fields import ValueDateField
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.api.utils.response import ErrorResponse, Response, MultiResponse
from main.apps.oems.backend.calendar_utils import infer_value_date

class InitialMarketStateRequestSerializer(serializers.Serializer):

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    value_date = ValueDateField(required=False, help_text=VALUE_DATE_HELP_TEXT, default='SPOT')
    subscription = serializers.BooleanField(default=True, help_text="Generate and return channel subscription")

@extend_schema_serializer(
    exclude_fields=['subscription','value_date']
)
class InitialRateRequestSerializer(serializers.Serializer):

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    value_date = ValueDateField(required=False, help_text=VALUE_DATE_HELP_TEXT, default='SPOT')
    subscription = serializers.BooleanField(default=False, help_text="Generate and return channel subscription")


MIN_DATA_START = datetime(2019,1, 1, 0, 0, 0, 0, pytz.UTC)

@extend_schema_serializer(
    exclude_fields=['periodicity','value_date'],
    examples=[
        OpenApiExample(
            name='HistoricalRateRequestByStartEndDate',
            value={
                "sell_currency": "USD",
                "buy_currency": "EUR",
                "start_date": datetime.now() - timedelta(days=3 * 30),
                "end_date": datetime.now(),
                "market_native": True
            },
        ),
        OpenApiExample(
            name='HistoricalRateRequestByDateRange',
            value={
                "sell_currency": "USD",
                "buy_currency": "EUR",
                "date_range": "3m|1y|5y",
                "market_native": True
            },
        ),
    ]
)
class HistoricalRateRequestSerializer(serializers.Serializer):

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    value_date = ValueDateField(required=False, help_text=VALUE_DATE_HELP_TEXT, default='SPOT')

    class Periodicity(models.TextChoices):
        DAILY = 'daily', 'daily'

    class DateRange(models.TextChoices):
        _3M = '3m', '3 Months'
        _1Y = '1y', '1 Year'
        _5Y = '5y', '5 Years'

    periodicity = serializers.ChoiceField(choices=Periodicity.choices, default=Periodicity.DAILY)
    start_date = serializers.DateTimeField(default=None, allow_null=True)
    end_date = serializers.DateTimeField(default=None, allow_null=True)
    market_native = serializers.BooleanField(default=True, help_text="Always show prices in market native")
    date_range = serializers.ChoiceField(choices=DateRange.choices, required=False, allow_null=True)

    def validate(self, attrs):

        sell_ccy = attrs.get('sell_currency')
        buy_ccy = attrs.get('buy_currency')

        if sell_ccy == buy_ccy:
            raise serializers.ValidationError('must provide two distinct currencies for rates')

        fxpair, side = determine_rate_side( sell_ccy, buy_ccy )

        attrs['fxpair'] = fxpair
        attrs['invert'] = (not attrs.get('market_native')) and (side == 'Sell')

        if not attrs.get('end_date'):
            attrs['end_date'] = datetime.utcnow()
            attrs['end_date'] = attrs['end_date'].replace(tzinfo=pytz.UTC)

        if not attrs.get('start_date'):
            attrs['start_date'] = attrs['end_date'] - timedelta(days=365)

        if attrs.get('date_range', None) is not None:
            now = datetime.utcnow().replace(tzinfo=pytz.UTC)
            if attrs['date_range'] == self.DateRange._3M:
                attrs['end_date'] = now
                attrs['start_date'] = now - relativedelta(months=3)
            elif attrs['date_range'] == self.DateRange._1Y:
                attrs['end_date'] = now
                attrs['start_date'] = now - relativedelta(years=1)
            elif attrs['date_range'] == self.DateRange._5Y:
                attrs['end_date'] = now
                attrs['start_date'] = now - relativedelta(years=5)

        if attrs['start_date'] < MIN_DATA_START:
            attrs['start_date'] = MIN_DATA_START

        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError('start date is after end date')

        return attrs

@extend_schema_serializer(
    exclude_fields=[]
)
class MarketVolatilitySerializer(serializers.Serializer):

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)
    value_date = ValueDateField(required=False, help_text=VALUE_DATE_HELP_TEXT, default='SPOT')

    def validate(self, attrs):

        sell_ccy = attrs.get('sell_currency')
        buy_ccy = attrs.get('buy_currency')

        if sell_ccy == buy_ccy:
            raise serializers.ValidationError('must provide two distinct currencies for risk')

        fxpair, side = determine_rate_side( sell_ccy, buy_ccy )

        attrs['fxpair'] = fxpair
        attrs['invert'] = (side == 'Sell')

        if attrs['value_date'] == '1M':
            attrs['value_date'] = None
        elif isinstance( attrs['value_date'], str):
            attrs['value_date'] = infer_value_date( fxpair.market, attrs['value_date'] )

        return attrs

class RecentVolResponseSerialier(serializers.Serializer):
    value_date = serializers.DateField()
    annual_volatility = serializers.FloatField()
    monthly_volatility = serializers.FloatField()
    daily_volatility = serializers.FloatField()
    volatility_at_t = serializers.FloatField()
    unit = serializers.CharField()


class OHLCMovingAvgSerializer(serializers.Serializer):
    open_ma = serializers.FloatField(allow_null=True)
    high_ma = serializers.FloatField(allow_null=True)
    low_ma = serializers.FloatField(allow_null=True)
    close_ma = serializers.FloatField(allow_null=True)


class RateMovingAverageSerializer(serializers.Serializer):
    date = serializers.DateField()
    rate = serializers.FloatField()
    rate_ma = serializers.FloatField()

class ohlcSerializer(serializers.Serializer):
    date = serializers.DateField()
    open = serializers.FloatField()
    high = serializers.FloatField()
    low = serializers.FloatField()
    close = serializers.FloatField()
    moving_avg = OHLCMovingAvgSerializer(required=False, allow_null=True)

class HistoricalRateResponseSerializer(serializers.ListSerializer):
    child = RateMovingAverageSerializer()

class BestExecutionSerializer(serializers.Serializer):
    market = serializers.CharField()
    recommend = serializers.BooleanField()
    session = serializers.CharField(required=False, allow_null=True)
    check_back = serializers.DateTimeField(required=False, allow_null=True),
    execute_before = serializers.DateTimeField(required=False, allow_null=True)
    unsupported = serializers.BooleanField()

class ExecutingBrokerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broker
        fields = [
            'id',
            'name',
            'broker_provider'
        ]

class InitialMarketStateResponseSerializer(serializers.Serializer):
    market = serializers.CharField()
    rate_rounding = serializers.IntegerField()
    side = serializers.CharField()
    spot_date = serializers.DateField()
    spot_rate = serializers.FloatField()
    rate = serializers.FloatField()
    fwd_points = serializers.FloatField()
    fwd_points_str = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    implied_yield = serializers.FloatField()
    indicative = serializers.BooleanField()
    cutoff_time = serializers.DateTimeField()
    as_of = serializers.DateTimeField()
    status = BestExecutionSerializer()
    channel_group_name = serializers.CharField()
    fee = serializers.FloatField()
    quote_fee = serializers.FloatField()
    wire_fee = serializers.FloatField(required=False, allow_null=True)
    pangea_fee = serializers.CharField()
    broker_fee = serializers.CharField()
    is_ndf = serializers.BooleanField(required=False, allow_null=True)
    fwd_rfq_type = serializers.CharField(required=False, allow_null=True)
    all_in_reference_rate = serializers.FloatField(required=False, allow_null=True)
    executing_broker = ExecutingBrokerSerializer(required=False, allow_null=True)
    is_same_currency = serializers.BooleanField()


class MarketRateSerializer(serializers.Serializer):
    ask = serializers.FloatField()
    bid = serializers.FloatField()
    mid = serializers.FloatField()
    date = serializers.SerializerMethodField()

    def get_date(self, obj) -> str:
        return str(obj['date']).replace('+00:00', 'Z')


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Recent market rate',
            value={
                "spot_rate": {
                    "ask": 0.8511468272569098,
                    "bid": 0.8503572353487806,
                    "mid": 0.8507601645979271,
                    "date": "2024-04-19 03:55:00+00:00"
                },
                "fwd_points": {
                    "ask": 0.00015835278728282276,
                    "bid": 0.00015397263555960716,
                    "mid": 0.00015618480124646172,
                    "date": "2024-04-24"
                },
                "ws-feed": None,
            },
        ),
    ]
)
class RecentRateResponseSerializer(serializers.Serializer):
    spot_rate = MarketRateSerializer()
    fwd_points = MarketRateSerializer()
    channel_group_name = serializers.CharField()
