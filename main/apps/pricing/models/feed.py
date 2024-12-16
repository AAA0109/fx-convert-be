from django.db import models
from django.utils.translation import gettext_lazy as _
from multiselectfield.db.fields import MultiSelectField

from main.apps.account.models import User, Company
from main.apps.oems.models.ticket import Ticket


class Feed(models.Model):
    feed_name = models.CharField(max_length=255)
    channel_group = models.CharField(max_length=255, blank=True, null=True)
    tick_type = models.CharField(max_length=100)
    indicative = models.BooleanField()
    raw = models.JSONField()
    feed_type = models.CharField(max_length=100, null=True, blank=True)
    collector_name = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)
    tag = models.CharField(max_length=512, editable=False, null=True,
                           blank=True)  # feed_name,channel_group,tick_type,feed_type,collector_name


class FeedInstrument(models.Model):
    class Type(models.TextChoices):
        SPOT = 'spot', _('Spot')
        FORWARD = 'forward', _('Deliverable Forward')
        NDF = 'ndf', _('Non-deliverable Forward')
        OPTION = 'option', _('Option')
        FUTURE = 'future', _('Future')

    instrument_type = models.CharField(max_length=50, choices=Type.choices)
    symbol = models.CharField(max_length=100)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    tenors = MultiSelectField(choices=Ticket.Tenors.choices, null=True, blank=True)

    def __str__(self):
        return f"{self.symbol}-{self.instrument_type}".upper()
