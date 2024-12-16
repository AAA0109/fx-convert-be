from main.apps.currency.models.deliverytime import DeliveryTime as BaseDeliveryTime
from main.apps.oems.models.cny import CnyExecution as BaseCnyExecution


class DeliveryTime(BaseDeliveryTime):

    class Meta:
        verbose_name = "Bank Country Session"
        verbose_name_plural = "Bank Country Sessions"
        proxy = True


class CnyExecution(BaseCnyExecution):

    class Meta:
        proxy = True
