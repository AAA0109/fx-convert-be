from rest_framework import serializers

from main.apps.account.models import Company


class CorPayCompanySettingsSerializer(serializers.Serializer):
    wallet = serializers.BooleanField()
    forwards = serializers.BooleanField()
    max_horizon = serializers.IntegerField()

    @staticmethod
    def company_can_use_wallet(company: Company) -> bool:
        return CorPayCompanySettingsSerializer.company_has_corpay_credentials(company)

    @staticmethod
    def company_can_use_forwards(company: Company) -> bool:
        return CorPayCompanySettingsSerializer.company_has_corpay_credentials(company)

    @staticmethod
    def company_has_corpay_credentials(company: Company):
        if not hasattr(company, 'corpaysettings'):
            return False
        if company.corpaysettings.user_id is not None and company.corpaysettings.signature is not None:
            return True
        return False

    @staticmethod
    def company_max_forward_horizon(company: Company):
        if not hasattr(company, 'corpaysettings'):
            return 0
        return company.corpaysettings.max_horizon
