import uuid

from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company
from main.apps.currency.models import Currency

class Beneficiary(TimeStampedModel):
    class Method(models.TextChoices):
        WIRE = 'W', 'Wire'
        EFT = 'E', 'EFT'
        FXBalance = 'C', 'FX Balance'

    corpay_id = models.CharField(max_length=255, null=True)
    client_code = models.CharField(max_length=32, null=True)
    client_integration_id = models.CharField(max_length=255, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    is_withdraw = models.BooleanField(default=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="corpay_beneficiaries")
    delivery_method = models.CharField(max_length=1, choices=Method.choices, null=True)


    @staticmethod
    def get_beneficiary_by_client_integration_id(integration_id: str, company: Company) -> 'Beneficiary':
        return Beneficiary.objects.get_or_create(client_integration_id=integration_id, company=company)

    @staticmethod
    def create_beneficiary_for_company(company: Company, is_withdraw: bool = False) -> 'Beneficiary':
        beneficiary = Beneficiary(
            client_integration_id=Beneficiary.generate_client_integration_uuid().hex,
            company=company,
            is_withdraw=is_withdraw
        )
        beneficiary.save()
        return beneficiary

    @staticmethod
    def generate_client_integration_uuid() -> uuid.UUID:
        """
        The 'clientIntegrationId' value is a unique beneficiary ID that you can use in other endpoints. The first time it is provided, it creates a new resource, which is later used to reference that beneficiary.

        The 'clientIntegrationId' must be unique as Corpay uses global values in this field.

        Note: The only characters allowed in the 'clientIntegrationId' are:

        Alphanumeric (a-zA-Z0-9)
        Dash (-)
        Underscore (_)
        You can use GUID which has a very low chance of collision, your own hash, or some determinstic prefix to make it unique.

        Changing the 'clientIntegrationId' creates a new beneficiary template.
        """
        return uuid.uuid4()


class BeneficiaryTemplate(TimeStampedModel):
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, null=False)
    template_id = models.CharField(max_length=60)

    @staticmethod
    def get_most_recent_template_id(beneficiary: Beneficiary):
        return BeneficiaryTemplate \
            .objects.filter(beneficiary=beneficiary) \
            .order_by('created', 'desc') \
            .first()
