from . import Cm, CmAsset
from django.db import models


class CmInstrument(models.Model):
    """
    A commodity instrument (e.g. a future .. for now, they are all assumed to just be futures)
    """
    asset = models.ForeignKey(CmAsset, on_delete=models.CASCADE, null=False)
    expiry = models.DateField(null=False)  # Expiry date of asset
    expiry_label = models.CharField(max_length=30, null=True)  # e.g. "MAR2022"

    def __str__(self) -> str:
        """ Return the name of the instrument (our internal ticker), e.g. Gold@MAR2022 """
        return f"{self.asset.name}@{self.expiry_label}"

    class Meta:
        # For now, the asset + expiry uniquely determine the future. If we get more contract types, then
        # it will be "asset", "contract_type", "expiry"
        unique_together = (("asset", "expiry"),)

    # ============================
    # Convenience Query Methods
    # ============================


class CmInstrumentData(Cm):
    """ Instrument Data"""
    instrument = models.ForeignKey(CmInstrument, on_delete=models.CASCADE, null=False)

    mid_price = models.FloatField(null=True)
    bid_price = models.FloatField(null=True)
    ask_price = models.FloatField(null=True)

    # ============================
    # Convenience Query Methods
    # ============================
