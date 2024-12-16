import logging
from typing import Iterable, List, Optional, Tuple, Union

from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext as _
from multiselectfield import MultiSelectField

from main.apps.account.models.company import Company, CompanyTypes
from main.apps.broker.models.constants import BrokerProviderOption, BrokerExecutionMethodOptions, \
    ExecutionTypes, ApiTypes, FundingModel
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.util import ActionStatus, get_or_none

logger = logging.getLogger(__name__)

BrokerID = int


class Broker(models.Model):
    """ Model for a broker, e.g. Interactive Brokers """
    name = models.CharField(max_length=255, null=False, unique=True)
    broker_provider = models.CharField(max_length=50, choices=BrokerProviderOption.choices, blank=True)
    execution_method = models.CharField(max_length=50, choices=BrokerExecutionMethodOptions.choices, null=True)
    supported_instruments = MultiSelectField(choices=InstrumentTypes.choices, help_text="Supported instrument",
                                             null=True, blank=True)
    minimum_rfq_expiry = models.IntegerField(blank=True, null=True)
    maximum_rfq_expiry = models.IntegerField(blank=True, null=True)

    # ================

    supported_execution_types = MultiSelectField(choices=ExecutionTypes.choices, help_text="Supported execution types",
                                                 null=True, blank=True)
    api_types = MultiSelectField(choices=ApiTypes.choices, help_text="Supported api types", null=True, blank=True)

    api_config = models.JSONField(
        null=True, blank=True,
        help_text='API config.'
    )

    funding_models = MultiSelectField(choices=FundingModel.choices, help_text="Supported funding models", null=True,
                                      blank=True)

    domicile = models.CharField(null=True, blank=True)
    contact_name = models.CharField(null=True, blank=True)
    contact_email = models.CharField(null=True, blank=True)

    def __str__(self):
        return self.name

    # ==================================================================
    #  Creation
    # ==================================================================

    @staticmethod
    def create_broker(name: str) -> Tuple[ActionStatus, Optional['Broker']]:
        broker, created = Broker.objects.get_or_create(name=name)
        status = ActionStatus.log_and_success(f"Created broker {name}") if created else \
            ActionStatus.log_and_no_change(f"Broker {name} already exists")
        return status, broker

    @staticmethod
    @get_or_none
    def get_broker(broker: Union[str, BrokerID, 'Broker']) -> Optional['Broker']:
        if isinstance(broker, Broker):
            return broker
        if isinstance(broker, str):
            return Broker.objects.get(name=broker)
        if isinstance(broker, BrokerID):
            return Broker.objects.get(pk=broker)
        raise ValueError("Invalid argument type for get_broker")


BrokerTypes = Union[str, BrokerID, Broker]


class BrokerAccountCapability(models.Model):
    class Meta:
        verbose_name_plural = 'Broker Account Capabilities'

    class Types(models.TextChoices):
        TRADE = 'trade', _('Trade'),
        FUND = 'fund', _('Fund'),
        BACKTEST = 'backtest', _('Backtest')

    type = models.CharField(max_length=10, choices=Types.choices, unique=True)

    def __str__(self):
        return self.type


class BrokerAccount(models.Model):
    class AccountType(models.IntegerChoices):
        LIVE = 1, _('Live')
        PAPER = 2, _('Paper')

    # The company for which this is a broker account.
    company = models.ForeignKey(Company, related_name='broker_accounts', null=False, on_delete=models.CASCADE)

    # The broker this account belongs with.
    broker = models.ForeignKey(Broker, null=False, on_delete=models.PROTECT)

    # The broker's name for this account. Note that this will be some broker specific identifier, like
    #  as an IB account, not a user nickname for an account.
    broker_account_name = models.CharField(max_length=255)

    # What type of account this is.
    account_type = models.IntegerField(choices=AccountType.choices, null=False)

    # What type of capability does this broker account support
    capabilities = models.ManyToManyField(BrokerAccountCapability)

    def __str__(self):
        return self.broker_account_name

    # ==================================================================
    #  Accessors
    # ==================================================================

    @staticmethod
    @get_or_none
    def get_account(account: Union['BrokerAccount', str]):
        if isinstance(account, BrokerAccount):
            return account
        if isinstance(account, str):
            BrokerAccount.objects.filter(broker_account_name=account)
        return None

    @staticmethod
    def get_accounts_for_company(company: CompanyTypes,
                                 account_types: Iterable[AccountType] = (AccountType.LIVE,)
                                 ) -> Optional[List['BrokerAccount']]:
        broker_accounts = [account for account in BrokerAccount.objects.filter(company=company,
                                                                               account_type__in=account_types)]
        return broker_accounts if 0 < len(broker_accounts) else None

    # ==================================================================
    #  Creation
    # ==================================================================

    @staticmethod
    def create_account_for_company(company: CompanyTypes,
                                   broker: Broker,
                                   broker_account_name: str,
                                   account_type: AccountType) -> Tuple[ActionStatus, Optional['BrokerAccount']]:
        account, created = BrokerAccount.objects.get_or_create(company=company,
                                                               broker=broker,
                                                               broker_account_name=broker_account_name,
                                                               account_type=account_type)
        status = ActionStatus.log_and_success(f"Created broker account {broker_account_name}") if created else \
            ActionStatus.log_and_no_change(f"Broker account {broker_account_name} already exists")
        return status, account

    @staticmethod
    def delete_company_accounts(company: CompanyTypes):
        # TODO: add some error handling, return action status
        BrokerAccount.objects.filter(company=company).delete()

    @staticmethod
    def has_ibkr_broker_account(company: Company):
        return BrokerAccount.objects.filter(company=company).filter(
            broker__name='IBKR',
            broker_account_name__isnull=False
        ).exists()


class BrokerCompany(models.Model):
    broker = models.CharField(choices=BrokerProviderOption.choices, max_length=255)
    brokers = models.ManyToManyField(Broker)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, unique=False)
    enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = (('broker', 'company'),)

    @staticmethod
    def get_company_brokers(company: Company):
        brokers = []
        try:
            brokers = list(
                BrokerCompany.objects.filter(company=company, enabled=True).distinct('broker').values_list('broker', flat=True))
        except Exception as e:
            logger.exception(e)
        return brokers

    @staticmethod
    def get_companies_by_broker(broker: str):
        companies = []
        try:
            companies = list(
                BrokerCompany.objects.filer(broker=broker, enabled=True).distinct('company').values_list('company', flat=True)
            )
        except Exception as e:
            logger.exception(e)

        return companies


auditlog.register(BrokerAccount)
auditlog.register(Broker)
