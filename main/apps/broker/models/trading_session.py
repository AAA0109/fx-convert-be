from django.db import models

from main.apps.broker.models.broker import Broker


class BrokerTradingSession(models.Model):

    class Meta:
        verbose_name = "Broker Trading Session"
        verbose_name_plural = "Broker Trading Sessions"

    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=False)

    broker_country = models.CharField(max_length=255, null=False)

    # Trading session open time in UTC
    session_open_utc = models.TimeField(help_text="Trading session open time in UTC")

    # Trading session close time in UTC
    session_close_utc = models.TimeField(help_text="Trading session close time in UTC")
