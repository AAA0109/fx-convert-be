from django.db import models
from django.utils.translation import gettext as _


class ExecutionTimingLabel(models.TextChoices):
    NOW = 'now', _("Now"),
    TODAY = 'today', _("Today"),
    TODAYS_CUTOFF = 'today_s__cutoff', _("Today's cutoff")
    TOMORROW = 'tomorrow', _("Tomorrow")
    TOMORROWS_CUTOFF = 'tomorrow_s__cutoff', _("Tomorrow's cutoff")

