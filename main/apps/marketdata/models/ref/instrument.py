import logging

from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext as _

from main.apps.oems.backend.utils import DateTimeEncoder

logger = logging.getLogger(__name__)


# ============================

# The order's instrument type choices
class InstrumentTypes(models.TextChoices):
    FXRATE = "fxrate", _("FxRate")
    FORWARD = "forward", _("Forward")
    FUTURE = 'future', _("Future")
    BASE_FUTURE = 'base_future', _("BaseFuture")
    CONTINUOUS_FUTURE = 'continuous_future', _("ContinuousFuture")
    CASH_EQUITY = 'cash_equity', 'CashEquity'
    OPTION = "option", _("Option")
    SPOT = "spot", _("Spot")
    WINDOW_FORWARD = "window_forward", "Window Forward"
    NDF = "ndf", _("Ndf")
    SWAP = "swap", _("Swap")
    NDS = "nds", _("Nds")
    RTP = "rtp", _("Realtime Payment")
    CONTINUOUS_SPOT = 'continuous_spot', 'Continuous Spot'
    CURRENCY = "currency", "Currency"


# ============================

class Instrument(models.Model):
    name = models.CharField(null=False)
    instrument_type = models.CharField(choices=InstrumentTypes.choices, help_text="instrument type", null=True,
                                       blank=True)
    tradable_instrument = models.BooleanField(default=False)
    base_instrument = models.CharField(blank=True, null=True)
    reference = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    symbology = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    multi_leg = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ============================

auditlog.register(Instrument)
