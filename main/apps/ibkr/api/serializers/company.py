from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.broker.models import BrokerAccount


class IbkrCompanySettingsSerializer(serializers.Serializer):
    spot = serializers.BooleanField()

    @staticmethod
    def company_can_trade_spot(company: Company) -> bool:
        return BrokerAccount.has_ibkr_broker_account(company)
