from . import Eq
from django.db import models


class EqSpot(Eq):
    # DO IF WE USE THIS: add bid, ask, high low, etc... similar to fx
    close = models.FloatField(null=True)

    class Meta:
        unique_together = (("date_time", "name"),)

    # ============================
    # Convenience Query Methods
    # ============================
