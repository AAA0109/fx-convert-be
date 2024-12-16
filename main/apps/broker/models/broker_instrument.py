from datetime import time, timedelta
from django.db import models

from main.apps.broker.models.broker import Broker
from main.apps.marketdata.models.ref.instrument import Instrument
from main.apps.broker.models.constants import FeeType, BrokerExecutionMethodOptions, ExecutionTypes, ApiTypes, FundingModel

from multiselectfield import MultiSelectField

# need to add USDUSD or USD to security master

class BrokerInstrument(models.Model):

    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=False)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, null=False)

    # currencies
    base_ccy = models.CharField(null=True, blank=True)
    counter_ccy = models.CharField(null=True, blank=True)

    # perms
    active = models.BooleanField(default=True)
    buy = models.BooleanField(default=False)
    sell = models.BooleanField(default=False)

    buy_wallet = models.BooleanField(default=False)
    sell_wallet = models.BooleanField(default=False)

    # broker costs if we have them
    buy_cost = models.FloatField(null=True, blank=True)
    buy_cost_unit = models.CharField(choices=FeeType.choices, null=True, blank=True,)
    sell_cost = models.FloatField(null=True, blank=True)
    sell_cost_unit = models.CharField(choices=FeeType.choices, null=True, blank=True,)

    # fees and other information
    buy_fee = models.FloatField(null=True, blank=True) # models.DecimalField(max_digits=19, decimal_places=9, default=0.00)
    buy_fee_unit = models.CharField(choices=FeeType.choices, null=True, blank=True,) # fee unit
    sell_fee = models.FloatField(null=True, blank=True) # models.DecimalField(max_digits=19, decimal_places=9, default=0.00)
    sell_fee_unit = models.CharField(choices=FeeType.choices, null=True, blank=True,) # fee unit

    # Currency delivery sla in business days
    delivery_sla = models.FloatField(default=0, verbose_name='Delivery SLA in hours',
                                    help_text='Delivery SLA in hours. e.g 0.5 for 30 minutes or 48 for 2 days')

    # Currency delivery deadline
    cutoff_time = models.TimeField(default=time(hour=21),
                                   verbose_name='Cutoff time in UTC',
                                   help_text='Cutoff time format hh:mm')

    funding_models = MultiSelectField(choices=FundingModel.choices, help_text="Supported funding models", null=True, blank=True)
    execution_types = MultiSelectField(choices=ExecutionTypes.choices, help_text="Supported execution types", null=True, blank=True)
    api_types = MultiSelectField(choices=ApiTypes.choices, help_text="Supported api types", null=True, blank=True)

    wire_fee = models.FloatField(null=True, blank=True) # models.DecimalField(max_digits=19, decimal_places=9, default=0.00)
    wire_fee_unit = models.CharField(choices=FeeType.choices, null=True, blank=True,) # fee unit

    custom = models.JSONField(
        null=True, blank=True,
        help_text='Custom Information.'
    )

    class Meta:
        unique_together = (('broker', 'instrument'),)  # Ensures unique pairings

    def __str__( self ):
        return f'{self.broker.name}-{self.instrument.name}'


