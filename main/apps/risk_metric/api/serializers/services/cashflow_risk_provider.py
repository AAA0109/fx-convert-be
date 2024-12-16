from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.account.models import CashFlow, BaseCashFlow
from main.apps.core.serializers.common import HDLDateField
from main.apps.currency.models import Currency

from hdlib.DateTime.Date import Date


class CashFlowsField(serializers.JSONField):
    def to_internal_value(self, data):
        _data = {}
        for foreign_mnemonic, foreign_cashflows in data.items():
            foreign_currency = Currency.get_currency(str(foreign_mnemonic))
            if foreign_currency is None:
                raise serializers.ValidationError("Invalid currency ID")
            _foreign_cashflows = []
            for foreign_cashflow in foreign_cashflows:
                pay_date = Date.from_str(date=foreign_cashflow['pay_date'])
                end_date_str = foreign_cashflow.get('end_date', None)
                end_date = None
                if end_date_str:
                    end_date = Date.from_str(date=end_date_str)
                amount = foreign_cashflow['amount']
                currency = foreign_currency
                name = foreign_cashflow['name']
                periodicity = foreign_cashflow.get('periodicity')
                calendar = BaseCashFlow.CalendarType.from_name(foreign_cashflow.get('calendar', "NULL_CALENDAR"))
                roll_convention = BaseCashFlow.RollConvention.from_name(
                    foreign_cashflow.get('roll_convention', "FOLLOWING"))

                _foreign_cashflows.append(CashFlow(
                    date=pay_date,
                    currency=currency,
                    amount=amount,
                    name=name,
                    description=name,
                    periodicity=periodicity,
                    calendar=calendar,
                    roll_convention=roll_convention,
                    end_date=end_date))
            _data[foreign_currency] = _foreign_cashflows
        data = _data
        return data


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Risk Cone with Std Dev",
            value={
                "domestic": 'USD',
                "cashflows": {
                    "GBP": [
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2021-11-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2022-12-01",
                            "name": "string",
                            "end_date": "2023-12-31",
                            "periodicity": "FREQ=DAILY;INTERVAL=10;COUNT=5",
                            "calendar": "NULL_CALENDAR",
                            "roll_convention": "FOLLOWING"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2022-02-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2022-03-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2022-04-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'GBP',
                            "pay_date": "2022-05-01",
                            "name": "string"
                        }
                    ],
                    "AUD": [
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2021-11-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2022-12-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2022-02-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2022-03-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2022-04-01",
                            "name": "string"
                        },
                        {
                            "amount": 1024.25,
                            "currency": 'AUD',
                            "pay_date": "2022-05-01",
                            "name": "string"
                        }
                    ]
                },
                "start_date": "2021-10-28",
                "end_date": "2021-12-17",
                "risk_reductions": [
                    0.0,
                    0.33,
                    0.66,
                    0.8
                ],
                "max_horizon": 730,
                "std_dev_levels": [
                    1, 2, 3, 4
                ],
                "do_std_dev_cones": True,
                "lower_risk_bound_percent": -5,
                "upper_risk_bound_percent": 3
            }
        )
    ]
)
class GetCashflowRiskConeSerializer(serializers.Serializer):
    domestic = serializers.CharField()
    cashflows = CashFlowsField()
    start_date = HDLDateField()
    end_date = HDLDateField()
    risk_reductions = serializers.ListField(child=serializers.FloatField(), required=False)
    max_horizon = serializers.IntegerField()
    lower_risk_bound_percent = serializers.FloatField(default=-1000000, required=False)
    upper_risk_bound_percent = serializers.FloatField(default=1000000, required=False)
    std_dev_levels = serializers.ListSerializer(child=serializers.IntegerField(), required=False)
    do_std_dev_cones = serializers.BooleanField()

class GetCashflowRiskConeResponseSerializer(serializers.Serializer):
    dates = serializers.ListSerializer(child=serializers.DateTimeField())
    means = serializers.ListSerializer(child=serializers.FloatField())
    uppers = serializers.ListSerializer(child=serializers.ListField(child=serializers.FloatField()))
    lowers = serializers.ListSerializer(child=serializers.ListField(child=serializers.FloatField()))
    upper_maxs = serializers.ListSerializer(child=serializers.FloatField())
    upper_max_percents = serializers.ListSerializer(child=serializers.FloatField())
    lower_maxs = serializers.ListSerializer(child=serializers.FloatField())
    lower_max_percents = serializers.ListSerializer(child=serializers.FloatField())
    initial_value = serializers.FloatField()
    previous_value = serializers.FloatField()
    update_value = serializers.FloatField()
    std_probs = serializers.ListField(child=serializers.FloatField())


class GetSingleFxPairRiskConeSerializer(serializers.Serializer):
    fx_pair = serializers.CharField()
    start_date = HDLDateField()
    end_date = HDLDateField()
    std_dev_levels = serializers.ListSerializer(child=serializers.IntegerField(), required=False)
    do_std_dev_cones = serializers.BooleanField()
