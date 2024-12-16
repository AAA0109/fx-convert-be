from django_filters import FilterSet
from rest_framework import serializers

from main.apps.account.api.serializers.user import UserSerializer
from main.apps.account.models import User
from main.apps.billing.models import Fee
from main.apps.hedge.models import FxPosition
from main.apps.history.models.account_management import UserActivity
from main.apps.ibkr.models import DepositResult


class HistoryRequestSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)


class ActivityUserSerializer(UserSerializer):
    class Meta:
        model = User
        fields = ['id']


class ActivitySerializer(serializers.Serializer):
    class Meta:
        model = UserActivity
        fields = ('created', 'user', 'activity_type', 'changes')

    created = serializers.DateTimeField()
    changes = serializers.SerializerMethodField()
    user = ActivityUserSerializer()
    activity_type = serializers.ChoiceField(choices=UserActivity.ActivityType.choices)

    def get_changes(self, obj: UserActivity):
        return obj.changes


class ActivityFilter(FilterSet):
    class Meta:
        model = UserActivity
        fields = {
            'created': ['gte', 'gt', 'lte', 'lt'],
        }


class BankStatementFilter(FilterSet):
    class Meta:
        model = DepositResult
        fields = {
            'funding_request__broker_account': ['exact'],
            'created': ['gte', 'gt', 'lte', 'lt'],
            'modified': ['gte', 'gt', 'lte', 'lt'],
            'status': ['iexact', 'in'],
        }


class BankStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositResult
        fields = ('description', 'amount', 'account', 'funding_request_id', 'date')

    description = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()
    funding_request_id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    def get_description(self, obj: DepositResult):
        return obj.description

    def get_amount(self, obj: DepositResult):
        return obj.amount

    def get_account(self, obj: DepositResult):
        return obj.funding_request.broker_account_id

    def get_funding_request_id(self, obj: DepositResult):
        if obj.funding_request:
            return obj.funding_request.id
        else:
            return None

    def get_date(self, obj: DepositResult):
        return obj.update_modified


class TradeFilter(FilterSet):
    class Meta:
        model = FxPosition
        fields = {
            'account': ['exact'],
            'fxpair__base_currency__mnemonic': ['exact'],
            'company_event__time': ['gte', 'gt', 'lte', 'lt'],
        }

    pass


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxPosition
        fields = ('fx_pair', 'units', 'price', 'date')

    fx_pair = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    def get_fx_pair(self, obj: FxPosition):
        return obj.fxpair.name

    def get_units(self, obj: FxPosition):
        obj.amount

    def get_price(self, obj: FxPosition):
        return obj.average_price[0]

    def get_date(self, obj: FxPosition):
        return obj.company_event.time


class ActivitiesSerializer(serializers.Serializer):
    activities = serializers.ListSerializer(child=ActivitySerializer())


class BankStatementsSerializer(serializers.ModelSerializer):
    statements = serializers.ListSerializer(child=BankStatementSerializer())


class FeeFilter(FilterSet):
    class Meta:
        model = Fee
        fields = {
            'incurred': ['gte', 'gt', 'lte', 'lt'],
            'recorded': ['gte', 'gt', 'lte', 'lt'],
            'due': ['gte', 'gt', 'lte', 'lt'],
            'settled': ['gte', 'gt', 'lte', 'lt'],
            'cashflow': ['exact'],
            'payment': ['exact'],
        }

    pass


class FeesPaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fee
        fields = ('description', 'amount', 'incurred', 'cashflow_id', 'incurred', 'recorded', 'due', 'settled')

    description = serializers.SerializerMethodField()
    cashflow_id = serializers.SerializerMethodField()
    incurred = serializers.DateTimeField()
    recorded = serializers.DateTimeField()
    due = serializers.DateTimeField()
    settled = serializers.DateTimeField()

    def get_description(self, obj):
        return obj.fee_type

    def get_cashflow_id(self, obj: Fee):
        if obj.cashflow:
            return obj.cashflow.id
        else:
            return None


class TradesSerializer(serializers.Serializer):
    trades = serializers.ListSerializer(child=TradeSerializer())
