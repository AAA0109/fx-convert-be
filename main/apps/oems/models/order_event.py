from django.db import models
from django.utils.translation import gettext_lazy as __

from django_extensions.db.models import TimeStampedModel


class OrderEvent(TimeStampedModel):
    rate = models.FloatField(null=True)
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    class Meta:
        abstract = True
