from typing import Optional, Dict

from drf_spectacular.utils import extend_schema
from rest_framework import serializers

from main.apps.broker.api.serializers.broker import BrokerAccountSerializer
from main.apps.account.models import Account, User
from main.apps.account.models.company import Company, CompanyContactOrder, CompanyJoinRequest
from main.apps.corpay.api.serializers.company import CorPayCompanySettingsSerializer
from main.apps.currency.models import Currency
from main.apps.core.serializers.fields.timezone import TimeZoneSerializerChoiceField
from main.apps.ibkr.api.serializers.company import IbkrCompanySettingsSerializer
from main.apps.ibkr.api.serializers.eca import IbkrApplicationSerializer
from main.apps.payment.api.serializers.company import PaymentCompanySettingsSerializer


class CreateCompanySerializer(serializers.Serializer):
    currency = serializers.CharField(required=True, trim_whitespace=True)
    name = serializers.CharField(required=True, trim_whitespace=True)

    def validate_currency(self, value):
        cny = Currency.get_currency(value)
        if not cny:
            raise serializers.ValidationError(f"Unknown currency: {value}")
        return value


class AccountCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('id', 'name')


class CompanySettingsSerializer(serializers.Serializer):
    corpay = CorPayCompanySettingsSerializer()
    ibkr = IbkrCompanySettingsSerializer()
    payment = PaymentCompanySettingsSerializer()


class CompanyRepSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class CompanySerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field='mnemonic',
        queryset=Currency.objects.all()
    )
    status = serializers.CharField(source='get_status_display', read_only=True)
    timezone = TimeZoneSerializerChoiceField(use_pytz=True)
    broker_accounts = BrokerAccountSerializer(many=True, read_only=True)
    acct_company = AccountCompanySerializer(many=True, read_only=True)
    ibkr_application = IbkrApplicationSerializer(many=True, required=False, read_only=True)
    rep = CompanyRepSerializer()
    show_pnl_graph = serializers.BooleanField(read_only=True)
    settings = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = '__all__'

    def get_rep(self, obj: Company) -> Optional[str]:
        return obj.rep.email if obj.rep else None

    def get_settings(self, obj: Company) -> CompanySettingsSerializer:
        settings = {
            "ibkr": {
                "spot": IbkrCompanySettingsSerializer.company_can_trade_spot(obj)
            },
            "corpay": {
                "wallet": CorPayCompanySettingsSerializer.company_can_use_wallet(obj),
                "forwards": CorPayCompanySettingsSerializer.company_can_use_forwards(obj),
                "max_horizon": CorPayCompanySettingsSerializer.company_max_forward_horizon(obj)
            },
            "payment": {
                "stripe": PaymentCompanySettingsSerializer.company_can_use_stripe(obj)
            }
        }

        return CompanySettingsSerializer(settings).data


class CompanyContactOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyContactOrder
        fields = '__all__'


class CompanyContactOrderRequestSerializer(serializers.Serializer):
    user_sort_order = serializers.ListField(child=serializers.IntegerField())


class GetCompanyByEINRequestSerializer(serializers.Serializer):
    ein = serializers.CharField()


class CompanyJoinRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyJoinRequest
        fields = '__all__'


class CreateCompanyJoinRequestSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()


class ApproveCompanyJoinRequestSerializer(serializers.Serializer):
    company_join_request_id = serializers.IntegerField()


class RejectCompanyJoinRequestSerializer(serializers.Serializer):
    company_join_request_id = serializers.IntegerField()
