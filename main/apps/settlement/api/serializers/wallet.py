from decimal import Decimal
from typing import Optional

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from main.apps.broker.api.serializers.broker import BrokerSerializer
from main.apps.core.constants import CURRENCY_HELP_TEXT
from main.apps.currency.models import Currency
from main.apps.settlement.models import Wallet, WalletBalance


class WalletBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletBalance
        fields = [
            'ledger_balance',
            'balance_held',
            'available_balance'
        ]

class WalletSerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field='mnemonic',
        queryset=Currency.objects.all(),
        help_text=CURRENCY_HELP_TEXT
    )
    latest_balance = serializers.SerializerMethodField()
    broker = BrokerSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'wallet_id',
            'company',
            'broker',
            'external_id',
            'currency',
            'name',
            'description',
            'account_number',
            'bank_name',
            'status',
            'type',
            'method',
            'latest_balance',
            'nickname',
            'default',
            'hidden',
        ]

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_latest_balance(self, obj) -> Optional[Decimal]:
        latest_balance = Wallet.get_latest_balance(obj)
        if latest_balance:
            return latest_balance.available_balance
        return None

class WalletUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model=Wallet
        fields=[
            'nickname',
            'default',
        ]
