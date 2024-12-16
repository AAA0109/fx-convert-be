from collections import OrderedDict
from typing import Optional, List

from hdlib.Hedge.Fx.HedgeAccount import HedgeMethod
from rest_framework import serializers
from rest_framework.fields import empty

from main.apps.account.api.serializers.autopilot_data import AutopilotDataSerializer
from main.apps.account.api.serializers.parachute_data import ParachuteDataSerializer
from main.apps.account.models import Account, User, Currency, ParachuteData
from main.apps.hedge.models import HedgeSettings


class HedgeSettingsCustomSettingsSerializer(serializers.Serializer):
    vol_target_reduction = serializers.FloatField()
    var_95_exposure_ratio = serializers.FloatField(required=False)
    var_95_exposure_window = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        if (
            ("vol_target_reduction" in instance) or
            ("var_95_exposure_ratio" in instance) or
            ("var_95_exposure_window" in instance)
        ):
            _instance = instance
        else:
            _instance = {}
        if "VolTargetReduction" in instance:
            _instance['vol_target_reduction'] = instance['VolTargetReduction']
        if "VaR95ExposureRatio" in instance:
            _instance['var_95_exposure_ratio'] = instance['VaR95ExposureRatio']
        if "VaR95ExposureWindow" in instance:
            _instance['var_95_exposure_window'] = instance['VaR95ExposureWindow']

        return super().to_representation(_instance)

    def to_internal_value(self, data):
        _data = super().to_internal_value(data)
        if ("VolTargetReduction" in data) or ("VaR95ExposureRatio" in data) or (
            "VaR95ExposureWindow" in data):
            _data = data
        else:
            _data = OrderedDict()
        if "vol_target_reduction" in data:
            _data['VolTargetReduction'] = data['vol_target_reduction']
        if "var_95_exposure_ratio" in data:
            _data['VaR95ExposureRatio'] = data['var_95_exposure_ratio']
        if "var_95_exposure_window" in data:
            _data['VaR95ExposureWindow'] = data['var_95_exposure_window']
        return _data


class AccountSummarySerializer(serializers.ModelSerializer):
    """
    A serializer representing condensed information about the account.
    """

    class Meta:
        model = Account
        fields = ['id', 'name']


class HedgeSettingsSerializer(serializers.ModelSerializer):
    custom = HedgeSettingsCustomSettingsSerializer(required=True)

    class Meta:
        model = HedgeSettings
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    type = serializers.CharField(source='get_type_display')
    hedge_settings = HedgeSettingsSerializer()
    parachute_data = ParachuteDataSerializer(required=False)
    autopilot_data = AutopilotDataSerializer(required=False)

    class Meta:
        model = Account
        fields = '__all__'


class CreateAccountForCompanyViewSerializer(serializers.Serializer):

    def __init__(self, user=None, instance=None, data=empty, **kwargs):
        super(CreateAccountForCompanyViewSerializer, self).__init__(instance=instance, data=data, **kwargs)
        self.user = user

    account_name = serializers.CharField()
    currencies = serializers.ListSerializer(child=serializers.CharField(), required=False)
    account_type = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False, allow_null=True)

    def get_account_type(self) -> Optional['Account.AccountType']:
        acct_type = self.data.get('account_type')
        try:
            return getattr(Account.AccountType, acct_type.upper())
        except:
            return None

    def validate_account_type(self, value):
        if value.upper() not in ["DRAFT", "DEMO", "LIVE"]:
            raise serializers.ValidationError(f"Unknown account_type {value}")
        else:
            return value

    def validate_account_name(self, account_name):
        accts = Account.get_account_objs(company=self.user.company_id)
        if account_name in [acct.name for acct in accts]:
            raise serializers.ValidationError(f"Account name already exists: {account_name}")
        return account_name

    def validate_currencies(self, value):
        return currencies_validator(self.user, value)


class HedgePolicyForAccountViewSerializer(serializers.Serializer):
    def __init__(self, user=None, instance=None, data=empty, **kwargs):
        super(HedgePolicyForAccountViewSerializer, self).__init__(instance=instance, data=data, **kwargs)
        self.user = user

    method = serializers.ChoiceField(
        choices=[(method.name, method.value) for method in HedgeMethod]
    )
    margin_budget = serializers.FloatField()
    max_horizon = serializers.IntegerField(required=False)
    custom = HedgeSettingsCustomSettingsSerializer(required=True)

    def validate_margin_budget(self, value):
        if value < 0:
            raise serializers.ValidationError(f"Margin budget shouldbe >= 0 {value}")
        return value

    def validate_max_horizon(self, value):
        if value < 0:
            raise serializers.ValidationError(f"Max horizon should be >= 0 {value}")
        return value

    def validate_method(self, value):
        if value.upper() not in [HedgeMethod.NO_HEDGE.value, HedgeMethod.PERFECT.value, HedgeMethod.MIN_VAR.value]:
            raise serializers.ValidationError(f"Unknown account_type {value}")
        else:
            return value


def currencies_validator(user: 'User', value: List[str]):
    for cny_mnemonic in value:
        cny = Currency.get_currency(cny_mnemonic)
        if not cny:
            raise serializers.ValidationError(f"Currency does not exist {value}")
    return value
