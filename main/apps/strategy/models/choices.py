from django.db import models


class Strategies(models.TextChoices):
    AUTOPILOT = 'autopilot', "Autopilot"
    PARACHUTE = 'parachute', "Parachute"
