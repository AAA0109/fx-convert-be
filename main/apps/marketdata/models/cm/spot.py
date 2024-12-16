from . import Cm
from django.db import models


class CmSpot(Cm):

    mid_price = models.FloatField(null=True)
    bid_price = models.FloatField(null=True)
    ask_price = models.FloatField(null=True)

    class Meta:
        pass
        # TODO: create a unique validate on Asset + date for the spot

    # ============================
    # Convenience Query Methods
    # ============================
