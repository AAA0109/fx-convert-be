from django_filters import rest_framework as filters

from main.apps.settlement.models import Wallet


class WalletFilter(filters.FilterSet):
    currency = filters.CharFilter(field_name='currency__mnemonic')
    type = filters.ChoiceFilter(choices=Wallet.WalletType.choices)
    status = filters.ChoiceFilter(choices=Wallet.WalletStatus.choices)
    method = filters.ChoiceFilter(choices=Wallet.WalletMethod.choices)

    class Meta:
        model = Wallet
        fields = ['currency', 'type', 'status', 'method']
