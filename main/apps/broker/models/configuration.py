from django.db import models
from django.utils.translation import gettext_lazy as _

from main.apps.broker.models import Broker
from main.apps.currency.models import Currency
from main.apps.marketdata.models.ref.instrument import InstrumentTypes


class ConfigurationTemplate(models.Model):
    class InstrumentTypes(models.TextChoices):
        SPOT = 'spot', _("Spot")
        FORWARD = "forward", _("Forward")
        NDF = "ndf", _("NDF")


    sell_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='sell_cny_broker_config_template')
    buy_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="buy_cny_broker_config_template")
    instrument_type = models.CharField(max_length=50, choices=InstrumentTypes.choices)
    preferred_broker = models.ForeignKey(Broker, on_delete=models.CASCADE)


class ConfigurationTemplateBroker(models.Model):
    configuration_template = models.ForeignKey(ConfigurationTemplate, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    api = models.BooleanField(default=False)


class FeeTemplate(models.Model):
    sell_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='sell_cny_fee_template')
    buy_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="buy_cny_fee_template")
    instrument_type = models.CharField(max_length=50, choices=InstrumentTypes.choices)
    broker_markup = models.DecimalField(max_digits=10, decimal_places=2)
