from rest_framework import serializers

from main.apps.account.models import Company


class PaymentCompanySettingsSerializer(serializers.Serializer):
    stripe = serializers.BooleanField()

    @staticmethod
    def company_can_use_stripe(company: Company) -> bool:
        if company.stripe_customer_id is not None:
            return True
        return False

