import uuid

from django.db import models


class Metric(models.Model):
    ai_model = models.UUIDField(default=uuid.uuid4, editable=False)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    avg_buy = models.FloatField(null=True)
    avg_sell = models.FloatField(null=True)
    avg_buy_saved = models.FloatField(null=True)
    avg_sell_gained = models.FloatField(null=True)
    avg_saved = models.FloatField(null=True)
    min_buy_saved = models.FloatField(null=True)
    min_sell_gained = models.FloatField(null=True)
    avg_execution_spread = models.FloatField(null=True)
    avg_start_spread = models.FloatField(null=True)
    spread_benefit = models.FloatField(null=True)
    max_execution_spread = models.FloatField(null=True)
    avg_wait = models.FloatField(null=True)
    min_wait = models.FloatField(null=True)
    max_wait = models.FloatField(null=True)
