from django.db import models
from django.utils.translation import gettext as _

from main.apps.oems.models.extensions  import DateTimeWithoutTZField


class TradingCalendarFincal(models.Model):

    class IrregularOption(models.TextChoices):
        HOLIDAY = "H", _("Holiday")
        NON_STANDARD_HOURS = "Y", _("Non Standard Hours")
        NORMAL = "N", _("Normal")
        WEEKEND = "W", _("Weekend")

    class IrregularSessionOption(models.TextChoices):
        CLOSED = "C", _("Closed")
        OPEN = "O", _("Open")
        TRADING = "T", _("Trading")
        NORMAL = "N", _("Normal")

    class NewHoursOption(models.TextChoices):
        NON_STANDARD_HOURS = "Y", _("Non Standard Hours")
        NORMAL = "N", _("Normal")

    trade_date = models.DateField()
    cen_code = models.CharField(max_length=5, null=False)
    market = models.CharField(max_length=255, null=False)
    irregular = models.CharField(max_length=255, choices=IrregularOption.choices, null=True, blank=True)
    irreg_sess = models.CharField(max_length=255, choices=IrregularSessionOption.choices,  null=True, blank=True)
    new_hours = models.CharField(max_length=255, choices=NewHoursOption.choices, null=True, blank=True)
    functions = models.CharField(max_length=255, null=True, blank=True)
    activity = models.CharField(max_length=255, null=True, blank=True)
    local_open = DateTimeWithoutTZField(null=True, blank=True)
    local_close = DateTimeWithoutTZField(null=True, blank=True)
    first_open = models.IntegerField(null=True, blank=True)
    last_open = models.IntegerField(null=True, blank=True)
    first_close = models.IntegerField(null=True, blank=True)
    last_close = models.IntegerField(null=True, blank=True)
    nyus_open = DateTimeWithoutTZField(null=True, blank=True)
    nyus_close = DateTimeWithoutTZField(null=True, blank=True)
    gmtt_open = models.DateTimeField(null=True, blank=True)
    gmtt_close = models.DateTimeField(null=True, blank=True)
    gmtoff_op = models.CharField(null=True, blank=True)
    fmtoff_cl = models.CharField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['cen_code']),
            models.Index(fields=['gmtt_open']),
            models.Index(fields=['gmtt_close']),
        ]
