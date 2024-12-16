from django.db import models
from django.utils.translation import gettext_lazy as __

from .mapping import Mapping

from main.apps.currency.models.fxpair import FxPair
from main.apps.currency.models.currency import Currency
from main.apps.marketdata.models.ir.discount import IrCurve


class Value(models.Model):
    class MappingType(models.TextChoices):
        STRING = 'text', __('Text')
        CURRENCY = 'currency', __('Currency')
        FX_PAIR = 'fxpair', __('FX Pair')
        IR_CURVE = 'ircurve', __('IR Curve')

    mapping = models.ForeignKey(Mapping, on_delete=models.CASCADE)
    mapping_type = models.CharField(max_length=20, choices=MappingType.choices, default=MappingType.STRING)
    from_value = models.CharField(max_length=255)
    to_value = models.CharField(max_length=255, null=True, blank=True)
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True)
    to_fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, verbose_name='To FX Pair', null=True, blank=True)
    to_ircurve = models.ForeignKey(IrCurve, on_delete=models.CASCADE, verbose_name='To IR Curve', null=True,
                                   blank=True)

    def __str__(self):
        if self.mapping_type == Value.MappingType.STRING:
            return self.from_value + "  |  " + self.to_value

        if self.mapping_type == Value.MappingType.CURRENCY:
            return self.from_value + "  |  " + self.to_currency.__str__()

        if self.mapping_type == Value.MappingType.FX_PAIR:
            return self.from_value + "  |  " + self.to_fxpair.__str__()

        if self.mapping_type == Value.MappingType.IR_CURVE:
            return self.from_value + "  |  " + self.to_ircurve.__str__()

        return self.from_value

    class Meta:
        verbose_name_plural = "Values"
