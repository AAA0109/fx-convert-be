from typing import Optional, Union
from django.db import models
from main.apps.util import get_or_none

from main.apps.oems.models.quote import Quote
from main.apps.oems.models.order_event import OrderEvent


class WaitCondition(OrderEvent):
    expected_saving = models.FloatField(null=True)
    expected_saving_percentage = models.FloatField(null=True)
    lower_bound = models.FloatField(null=True)
    regime = models.IntegerField(null=True)
    upper_bound = models.FloatField(null=True)
    start_time = models.DateTimeField(null=True)
    recommendation_time = models.DateTimeField(null=True)
    ai_model = models.CharField(null=True, max_length=256)
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, related_name='wait_condition_quote')

    @staticmethod
    @get_or_none
    def get_waitcondition_by_quote(quote: Union[int, 'Quote']) -> Optional['WaitCondition']:
        if isinstance(quote, int):
            return WaitCondition.objects.get(quote__id=quote)
        elif isinstance(quote, Quote):
            return WaitCondition.objects.get(quote=quote)
        return None
