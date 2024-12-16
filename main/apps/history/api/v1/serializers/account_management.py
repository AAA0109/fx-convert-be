from rest_framework import serializers
from main.apps.currency.api.serializers.models.currency import CurrencySerializer


class HistoryRequestSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)


class ActivitySerializer(serializers.Serializer):
    description = serializers.CharField()
    date = serializers.DateTimeField()


class BankStatementSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.FloatField()
    account = serializers.CharField()
    draft = serializers.IntegerField()
    date = serializers.DateTimeField()


class FeePaymentSerializer(serializers.Serializer):
    description = serializers.CharField()
    account_hedge_request_id = serializers.IntegerField(allow_null=True)
    amount = serializers.FloatField()
    date = serializers.DateTimeField()


class TradeSerializer(serializers.Serializer):
    currency = CurrencySerializer()
    units = serializers.IntegerField()
    price = serializers.FloatField()
    date = serializers.DateTimeField()


class ActivitiesSerializer(serializers.Serializer):
    activities = serializers.ListSerializer(child=ActivitySerializer())


class BankStatementsSerializer(serializers.Serializer):
    statements = serializers.ListSerializer(child=BankStatementSerializer())


class FeesPaymentsSerializer(serializers.Serializer):
    fees_and_payments = serializers.ListSerializer(child=FeePaymentSerializer())


class TradesSerializer(serializers.Serializer):
    trades = serializers.ListSerializer(child=TradeSerializer())
