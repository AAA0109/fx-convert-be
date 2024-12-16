from typing import Optional

from django.db import models

from main.apps.account.models import Company
from main.apps.util import get_or_none



class CorpaySettings(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, null=False, related_name='corpaysettings')
    client_code = models.IntegerField(null=False)
    signature = models.CharField(max_length=60, null=False)
    average_volume = models.IntegerField(null=False, default=0)
    credit_facility = models.FloatField(null=False, default=0.0)
    max_horizon = models.IntegerField(null=False, default=365)
    fee_wallet_id = models.CharField(max_length=255, null=True, blank=True)
    pangea_beneficiary_id = models.CharField(max_length=255, null=True, blank=True)
    user_code = models.IntegerField(null=True, blank=True)

    @property
    def user_id(self) -> str:
        code = self.user_code or self.client_code
        return f"{code}_API_User"

    @staticmethod
    @get_or_none
    def get_settings(company: Company) -> Optional['CorpaySettings']:
        return CorpaySettings.objects.get(company=company)


