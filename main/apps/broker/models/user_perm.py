from django.db import models

from main.apps.broker.models.broker_instrument import BrokerInstrument
from main.apps.broker.models.constants import RfqTypes
from main.apps.account.models.company import Company
from main.apps.account.models.user import User

# =====

class BrokerUserInstrument(models.Model):

    class Meta:
        unique_together = (('user','company','broker_instrument'),)

    user  = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    broker_instrument = models.ForeignKey(BrokerInstrument, on_delete=models.CASCADE, null=False)

    role = models.CharField(max_length=255, null=True, blank=True, default="admin")
    staging = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    default_exec_strat = models.CharField(max_length=255, null=False, default='MARKET')
    default_hedge_strat = models.CharField(max_length=255, null=False, default='SELFDIRECTED')
    default_algo = models.CharField(max_length=255, null=False, default="MARKET")
    use_triggers = models.BooleanField(default=True)
    
    rfq_type = models.CharField(
        choices=RfqTypes.choices, max_length=16, null=False, default=RfqTypes.UNSUPPORTED,
    )

    min_order_size_buy = models.FloatField(default=0.01)
    max_order_size_buy = models.FloatField(default=5000000.0)
    min_order_size_sell = models.FloatField(default=0.01)
    max_order_size_sell = models.FloatField(default=5000000.0)
    max_daily_tickets = models.IntegerField(default=100)
    unit_order_size_buy = models.FloatField(default=0.0)
    unit_order_size_sell = models.FloatField(default=0.0)
    max_tenor_months = models.IntegerField(default=12)
    