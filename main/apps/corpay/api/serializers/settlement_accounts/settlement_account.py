from rest_framework import serializers

from main.apps.corpay.api.serializers.base import LinkSerializer
from main.apps.corpay.api.serializers.choices import SETTLEMENT_ACCOUNT_DELIVERY_METHODS
from main.apps.corpay.models import FXBalance, FXBalanceDetail, FXBalanceAccount
from main.apps.currency.models import Currency
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider


class MethodSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()


class SettlementAccountChildrenSerializer(serializers.Serializer):
    id = serializers.CharField()
    method = MethodSerializer()
    currency = serializers.CharField()
    text = serializers.CharField()
    payment_ident = serializers.CharField(source='paymentIdent')
    bank_name = serializers.CharField(source='bankName')
    bank_account = serializers.CharField(source='bankAccount')
    preferred = serializers.BooleanField()
    selected = serializers.BooleanField()
    links = LinkSerializer(many=True)
    delivery_method = serializers.ChoiceField(choices=SETTLEMENT_ACCOUNT_DELIVERY_METHODS)

    def to_representation(self, instance):
        instance['delivery_method'] = instance['method']['id']
        instance = super().to_representation(instance)
        return instance


class SettlementAccountSerializer(serializers.Serializer):
    ordnum = serializers.IntegerField()
    text = serializers.CharField()
    children = SettlementAccountChildrenSerializer(many=True)


class SettlementAccountsResponseSerializer(serializers.Serializer):
    items = SettlementAccountSerializer(many=True)


class FXBalanceAccountsRequestSerializer(serializers.Serializer):
    include_balance = serializers.BooleanField(default=True)


class FXBalanceAccountsResponseDataRowSerializer(serializers.Serializer):
    account = serializers.CharField()
    currency = serializers.CharField()
    ledger_balance = serializers.FloatField(source='ledgerBalance')
    balance_held = serializers.FloatField(source='balanceHeld')
    available_balance = serializers.FloatField(source='availableBalance')
    ledger_balance_domestic = serializers.FloatField(required=False)
    balance_held_domestic = serializers.FloatField(required=False)
    available_balance_domestic = serializers.FloatField(required=False)
    account_number = serializers.CharField(source='accountNumber')
    client_code = serializers.IntegerField(source='clientCode')
    client_division_id = serializers.IntegerField(source='clientDivisionId')
    links = LinkSerializer(many=True)

    def to_representation(self, instance):
        spot_provider = FxSpotProvider()
        company = self.context['company']
        domestic_currency = company.currency
        if instance['currency'] == company.currency.mnemonic:
            instance['ledger_balance_domestic'] = instance['ledgerBalance']
            instance['balance_held_domestic'] = instance['balanceHeld']
            instance['available_balance_domestic'] = instance['availableBalance']
        else:
            account_currency = Currency.get_currency(instance['currency'])
            instance['ledger_balance_domestic'] = spot_provider.convert_currency_rate(
                account_currency,
                domestic_currency,
                instance['ledgerBalance']
            )
            instance['balance_held_domestic'] = spot_provider.convert_currency_rate(
                account_currency,
                domestic_currency,
                instance['balanceHeld']
            )
            instance['available_balance_domestic'] = spot_provider.convert_currency_rate(
                account_currency,
                domestic_currency,
                instance['availableBalance']
            )
        return super().to_representation(instance)


class FXBalanceAccountsResponseItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()
    curr = serializers.CharField()
    curr_text = serializers.CharField(source='currText')
    account = serializers.CharField()
    ledger_balance = serializers.FloatField(source='ledgerBalance')
    balance_held = serializers.FloatField(source='balanceHeld')
    available_balance = serializers.FloatField(source='availableBalance')
    allowed_payment = serializers.FloatField(source='allowedPayment')
    client = serializers.CharField()
    branch_id = serializers.IntegerField(source='branchId')
    account_name = serializers.CharField(source='accountName')
    links = LinkSerializer(many=True)


class FXBalanceAccountsResponseDataSerializer(serializers.Serializer):
    rows = FXBalanceAccountsResponseDataRowSerializer(many=True)


class FXBalanceAccountsResponseSerializer(serializers.Serializer):
    data = FXBalanceAccountsResponseDataSerializer()
    items = FXBalanceAccountsResponseItemSerializer(many=True)


class FXBalanceHistoryRequestSerializer(serializers.Serializer):
    fx_balance_id = serializers.CharField()
    ordering = serializers.CharField(default='-id')
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    include_details = serializers.BooleanField(required=False)


class FXBalanceAccountHistoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = FXBalanceDetail
        fields = ['transaction_id', 'identifier', 'name', 'currency', 'amount', 'date']


class FXBalanceAccountHistoryRowSerializer(serializers.ModelSerializer):
    details = FXBalanceAccountHistoryDetailSerializer(many=True)

    class Meta:
        model = FXBalance
        fields = ['id', 'order_number', 'date', 'amount', 'is_posted', 'balance', 'details']


class CompanyFXBalanceAccountHistoryDetailSerializer(serializers.ModelSerializer):
    currency = serializers.StringRelatedField()

    class Meta:
        model = FXBalanceDetail
        fields = [
            'transaction_id',
            'order_number',
            'identifier',
            'name',
            'currency',
            'amount',
            'date'
        ]


class CompanyFXBalanceAccountHistorySerializer(serializers.ModelSerializer):
    currency = serializers.StringRelatedField()
    details = CompanyFXBalanceAccountHistoryDetailSerializer(many=True)

    class Meta:
        model = FXBalance
        fields = [
            'id',
            'account_number',
            'date',
            'order_number',
            'amount',
            'debit_amount',
            'credit_amount',
            'is_posted',
            'balance',
            'currency',
            'details'
        ]
        depth = 1


class FXBalanceAccountSerializer(serializers.ModelSerializer):
    currency = serializers.StringRelatedField()

    class Meta:
        model = FXBalanceAccount
        fields = [
            "account_number",
            "account",
            "description",
            "ledger_balance",
            "balance_held",
            "available_balance",
            "client_code",
            "client_division_id",
            "company",
            "currency"
        ]
