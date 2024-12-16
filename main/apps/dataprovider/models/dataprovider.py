from django.utils.translation import gettext_lazy as __
from django.db import models

from main.apps.broker.models import Broker


class DataProvider(models.Model):
    class ProviderHandlers(models.TextChoices):
        REUTERS = 'reuters', __("Reuters"),
        ICE = 'ice', __("ICE"),
        CORPAY = 'corpay', __('CorPay'),
        IBKR = 'ibkr', __("IBKR"),
        NDL = 'ndl', __('Nasdaq Data Link'),
        COUNTRY = 'country', __('Country ISO Codes'),
        SPI = 'spi', __('Social Progress Index')
        FIN_CAL = 'fin_cal', __('Fin Cal')

    provider_handler = models.CharField(max_length=255, choices=ProviderHandlers.choices, default=None)
    broker = models.ForeignKey(Broker, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "    Data Providers"
