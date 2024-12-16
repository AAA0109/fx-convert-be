from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models import Company
from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import FxPair

from main.apps.broker.models.constants import BrokerProviderOption

class CnyExecution(models.Model):
    """
    This model is used to control the execution configuration for each FX pair a company is allowed to trade.
    """

    class Meta:
        db_table = 'cny_execution'
        unique_together = (('company', 'fxpair'),)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    staging = models.BooleanField(default=False)

    # default_broker = models.CharField(
    #    choices=BrokerProviderOption.choices, max_length=32, default='CORPAY'
    #)
    
    spot_broker = models.CharField(
        choices=BrokerProviderOption.choices, max_length=32, default='CORPAY'
    )
    fwd_broker = models.CharField(
        choices=BrokerProviderOption.choices, max_length=32, default='CORPAY'
    )

    class RfqTypes(models.TextChoices):
        API = 'api','API'
        MANUAL = 'manual', 'MANUAL'
        UNSUPPORTED = 'unsupported', 'UNSUPPORTED'
        INDICATIVE = 'indicative', 'INDICATIVE'
        NORFQ = 'norfq', 'NORFQ'
        
    spot_rfq_type = models.CharField(
        choices=RfqTypes.choices, max_length=16, null=False, default=RfqTypes.UNSUPPORTED,
    )

    fwd_rfq_type = models.CharField(
        choices=RfqTypes.choices, max_length=16, null=False, default=RfqTypes.UNSUPPORTED,
    )

    spot_rfq_dest = models.CharField(max_length=255, null=False, default="RFQ")
    fwd_rfq_dest = models.CharField(max_length=255, null=False, default="RFQ")
    spot_dest = models.CharField(max_length=255, null=False, default="CORPAY")
    fwd_dest = models.CharField(max_length=255, null=False, default="CORPAY")
    use_triggers = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Tenors(models.TextChoices):
        ON = 'ON', 'ON'
        TN = 'TN', 'TN'
        SPOT = 'spot', 'Spot'
        SN = 'SN', 'SN'
        SW = 'SW', 'SW'
        _1W = '1W', '1W'
        _2W = '2W', '2W'
        _3W = '3W', '3W'
        _1M = '1M', '1M'
        _2M = '2M', '2M'
        _3M = '3M', '3M'
        _4M = '4M', '4M'
        _5M = '5M', '5M'
        _6M = '6M', '6M'
        _7M = '7M', '7M'
        _8M = '8M', '8M'
        _9M = '9M', '9M'
        _1Y = '1Y', '1Y'
        IMM1 = 'IMM1', 'IMM1'
        IMM2 = 'IMM2', 'IMM2'
        IMM3 = 'IMM3', 'IMM3'
        IMM4 = 'IMM4', 'IMM4'
        EOM1 = 'EOM1', 'EOM1'
        EOM2 = 'EOM2', 'EOM2'
        EOM3 = 'EOM3', 'EOM3'
        EOM4 = 'EOM4', 'EOM4'
        EOM5 = 'EOM5', 'EOM5'
        EOM6 = 'EOM6', 'EOM6'
        EOM7 = 'EOM7', 'EOM7'
        EOM8 = 'EOM8', 'EOM8'
        EOM9 = 'EOM9', 'EOM9'
        EOM10 = 'EOM10', 'EOM10'
        EOM11 = 'EOM11', 'EOM11'
        EOM12 = 'EOM12', 'EOM12'

    max_tenor = models.CharField(
        choices=Tenors.choices, max_length=10, default=Tenors._1Y,
        help_text="The maximum allowed tenor of the transaction."
    )

    # fut_base = models.CharField(max_length=5, null=False, default="")

    # TODO: list available brokers
    # TODO: list available algorithms
    # TODO:

    @property
    def broker_accounts(self):
        accounts = BrokerAccount.get_accounts_for_company(self.company)
        if not accounts:
            return []
        return [acct.broker_account_name for acct in accounts]

auditlog.register(CnyExecution)
