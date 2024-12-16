from django.db import models
from django.utils.translation import gettext_lazy as _


class DestinationAccountType(models.TextChoices):
    W = "W", _("Wire")
    E = "E", _("iACH")
    C = "C", _("FXBalance")


class Locksides(models.TextChoices):
    Payment = "Payment", _("PAYMENT")
    Settlement = "Settlement", _("SETTLEMENT")


class RateOperation(models.TextChoices):
    Divide = "Divide", _("DIVIDE")
    Multiply = "Multiply", _("MULTIPLY")
