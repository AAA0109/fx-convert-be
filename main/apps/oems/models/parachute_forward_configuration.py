from typing import Tuple, Optional

from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models import Company
from main.apps.currency.models import FxPair


class CompanyParachuteForwardConfiguration:
    """
    Local structure that holds the configuration for a company's parachute forwards.
    Create this once for a company so that we don't have to query the database every time we need to get the
    configuration.
    """

    def __init__(self, company: Company, data_per_fxpair: dict):
        self.company = company
        self.data_per_fxpair = data_per_fxpair

    def get_data_for_fxpair(self, fxpair: FxPair) -> Optional[Tuple[float, bool]]:
        return self.data_per_fxpair.get(fxpair, None)


class ParachuteForwardConfiguration(models.Model):
    """
    This model is used to control orders for forwards while using parachute. Specifically, it controls order sizes and
    rounding.
    """

    class Meta:
        unique_together = (('company', 'fxpair'),)

    # The company this parachute forward configuration is for.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    # The FX pair that this execution configuration is for.
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    # The smallest order size (in absolute value) that can be placed.
    min_order_size = models.FloatField(default=0.0)

    # If true, the system will use multiples of the min_order_size to place orders.
    use_multiples = models.BooleanField(default=False)

    @staticmethod
    def add_config(company: Company,
                   fxpair: FxPair,
                   min_order_size: float,
                   use_multiples: bool) -> 'ParachuteForwardConfiguration':
        """
        Add a configuration for a company and an FX pair.
        """
        return ParachuteForwardConfiguration.objects.update_or_create(company=company, fxpair=fxpair,
                                                                      min_order_size=min_order_size,
                                                                      use_multiples=use_multiples)

    @staticmethod
    def create_company_parachute_forward_configuration(company: Company):
        """ Create a CompanyParachuteForwardConfiguration object from the data in the database."""
        data_per_fxpair = {}
        for config in ParachuteForwardConfiguration.objects.filter(company=company):
            data_per_fxpair[config.fxpair] = (config.min_order_size, config.use_multiples)
        return CompanyParachuteForwardConfiguration(company=company, data_per_fxpair=data_per_fxpair)


auditlog.register(ParachuteForwardConfiguration)
