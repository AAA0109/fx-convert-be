from django.db import models


class LockSides(models.TextChoices):
    FROM = "from", "From",
    TO = "to", "To"
