import logging
from typing import Sequence, Optional, Tuple, Union

from auditlog.registry import auditlog
from django.db import models
from django_countries.fields import CountryField
from django_extensions.db.models import TimeStampedModel
from django.utils.translation import gettext_lazy as _
from hdlib.Core.CompanyInterface import CompanyInterface
from hdlib.DateTime.Date import Date
from localflavor.us.models import USStateField, USZipCodeField
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField
from timezone_field import TimeZoneField

from main.apps.currency.models.currency import Currency, CurrencyTypes
from main.apps.util import get_or_none

logger = logging.getLogger(__name__)

# =====================================
# Type Definitions
# =====================================
CompanyName = str
CompanyId = int


class Company(models.Model, CompanyInterface):
    """
    Represents a company / customer of HD. A company can have multiple accounts
    """

    class Meta:
        verbose_name_plural = "companies"

    # Name of the company
    name = models.CharField(max_length=255, unique=True, null=False)

    # Legal Name of company
    legal_name = models.CharField(max_length=255, null=True, blank=True)

    # company phone
    phone = PhoneNumberField(null=True, blank=True)

    # company address line 1
    address_1 = models.CharField(max_length=255, null=True, blank=True)

    # company address line 2
    address_2 = models.CharField(max_length=255, null=True, blank=True)

    # company city
    city = models.CharField(max_length=255, null=True, blank=True)

    # company state
    state = USStateField(null=True, blank=True)

    # company zip code
    zip_code = USZipCodeField(null=True, blank=True)

    # region
    region = models.CharField(max_length=255, null=True, blank=True)

    # postal
    postal = models.CharField(max_length=255, null=True, blank=True)

    # country
    country = CountryField(default='US', null=True, blank=True)

    # company EIN
    ein = models.CharField(max_length=255, null=True, blank=True)

    # domain
    domain = models.CharField(max_length=255, null=True, blank=True)

    # company is non-profit
    nonprofit = models.BooleanField(default=False)

    # company is onboarded
    onboarded = models.BooleanField(default=False, verbose_name='Client Services Agreement Signed')

    # timezone
    timezone = TimeZoneField(default='UTC')

    # company account owner
    account_owner = models.ForeignKey('account.User', related_name='account_owner_company', on_delete=models.SET_NULL,
                                      null=True)

    # company account manager (Pangea employee)
    rep = models.ForeignKey('account.User', related_name='managed_companies', on_delete=models.SET_NULL,
                            null=True)

    # company notification recipients
    recipients = models.ManyToManyField('account.User', related_name='recipients_companies', blank=True)

    # When this company was added/created in our system
    created = models.DateTimeField(auto_now_add=True, blank=True)

    # The primary / default currency for this company
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT,
                                 related_name='comp_currency', null=False, verbose_name='Reporting Currency')

    class CompanyStatus(models.IntegerChoices):
        ACTIVE = 1  # An active company
        DEACTIVATED = 2  # A deactivated company
        DEACTIVATION_PENDING = 3  # A company who has requested deactivation, but it is not fully complete

    # Status of the company
    status = models.IntegerField(null=False, default=CompanyStatus.ACTIVE, choices=CompanyStatus.choices)

    # Stripe customer id
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)

    # Stripe setup intent id
    stripe_setup_intent_id = models.CharField(max_length=255, null=True, blank=True)

    # Hubspot Company id
    hs_company_id = models.BigIntegerField(null=True, blank=True)

    class ServiceInterestedIn(models.TextChoices):
        FX_HEDGING = 'fx_hedging', _("FX Hedging")
        WALLET = 'wallet', _('Wallet')
        PAYMENT = 'payment', _('Payment & Transfer')

    # Service Interested In
    service_interested_in = MultiSelectField(choices=ServiceInterestedIn.choices, null=True, blank=True)

    class EstimatedAumType(models.TextChoices):
        AUM_UNDER_10M = "0_10m", _("0-$10,000,000")
        AUM_10M_TO_100M = "10m_100m", _("$10,000,000 - $100,000,000")
        AUM_100M_TO_1B = "100m_1b", _("$100,000,000 - $1000,000,000")
        AUM_ABOVE_1B = "1b+", _("$1000,000,000+")

    # Estimated AUM
    estimated_aum = models.CharField(max_length=50, null=True, choices=EstimatedAumType.choices, blank=True)

    # Show pnl graph
    show_pnl_graph = models.BooleanField(default=True)

    def has_live_accounts(self, acct_types=None):
        if acct_types is None:
            acct_types = (2,)
        return self.acct_company.all().filter(type__in=acct_types).filter(is_active=True).exists()

    # =============================================================
    #  FxPairInterface methods.
    # =============================================================

    def get_name(self) -> str:
        return self.name

    def get_company_currency(self) -> Currency:
        return self.currency

    def __str__(self):
        """ Need to override __str__ since both model and CompanyInterface implement this. """
        return self.get_name()

    def __repr__(self):
        """ Need to override __str__ since both model and CompanyInterface implement this. """
        return self.get_name()

    # =============================================================
    #  Other methods.
    # =============================================================

    def is_ready_to_hedge(self):
        logger.debug(f"is_ready_to_hedge: Checking if {self.name} ({self.id}) is_ready_to_hedge?")
        from main.apps.broker.models import BrokerAccount
        from main.apps.corpay.models import CorpaySettings

        # company should be active
        is_company_active: bool = self.status == Company.CompanyStatus.ACTIVE
        logger.debug(f"is_ready_to_hedge: is_company_active={is_company_active}")

        # company should have a live broker account
        has_live_broker_account: bool = (
            self.broker_accounts
            .filter(broker_account_name__isnull=False)
            .filter(account_type=BrokerAccount.AccountType.LIVE).exists()
        )
        logger.debug(f"is_ready_to_hedge: has_live_broker_account={has_live_broker_account}")

        # company should have valid corpay settings
        corpay_settings: CorpaySettings = CorpaySettings.get_settings(company=self)
        has_valid_corpay_settings: bool = (
            corpay_settings and
            isinstance(corpay_settings.client_code, int) and
            corpay_settings.signature.__len__() > 0
        )
        logger.debug(f"is_ready_to_hedge: has_valid_corpay_settings={has_valid_corpay_settings}")

        is_ready_to_hedge: bool = is_company_active and (
            has_live_broker_account or has_valid_corpay_settings
        )
        logger.debug(f"is_ready_to_hedge: Check completed - "
                    f"{self.name} ({self.id}) is_ready_to_hedge={is_ready_to_hedge}")

        return is_ready_to_hedge


    # ============================
    # Accessors
    # ============================

    @staticmethod
    @get_or_none
    def get_company(company: Union[CompanyId, CompanyName, 'Company']) -> Optional['Company']:
        """
        Get a company object from any one of its unique identifiers
        :param company: CompanyTypes, any unique identifier
        :return: Company object (if found), else None
        """
        if isinstance(company, CompanyId):
            return Company.objects.get(id=company)
        if isinstance(company, CompanyName):
            return Company.objects.get(name=company)
        if isinstance(company, Company):
            return company
        raise ValueError("Unsupported input type for company search")

    @staticmethod
    def get_companies(status: Optional[Tuple[CompanyStatus]] = (CompanyStatus.ACTIVE,)) -> Sequence['Company']:
        """
        Get companies by status. By default, only active companies are returned.
        :param status: Tuple[CompanyStatus], only companies with these statuses are returned
        :return: Sequence of Company objects
        """
        companies = Company.objects.all()
        if status is not None:
            companies = companies.filter(status__in=status)

        return companies

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def create_company(name: str, currency: CurrencyTypes) -> 'Company':
        """
        Create a new company
        :param name: str, name of the company (must be unique)
        :param currency: Currency identifier, the domestic currency used for this company by default
        :return: ActionStatus, Company object
        """
        currency_ = Currency.get_currency(currency=currency)
        if not currency:
            raise Currency.NotFound(currency)
        company, created = Company.objects.get_or_create(name=name,
                                                         currency=currency_,
                                                         defaults={'created': Date.now()})
        return company

    # ============================
    # Exceptions
    # ============================

    class NotFound(Exception):
        def __init__(self, company: Union[CompanyId, CompanyName, 'Company']):
            if isinstance(company, CompanyId):
                super(Company.NotFound, self).__init__(f"Company with id:{company} is not found")
            elif isinstance(company, CompanyName):
                super(Company.NotFound, self).__init__(f"Company with name:{company} is not found")
            elif isinstance(company, Company):
                super(Company.NotFound, self).__init__(f"Company:{company} is not found")
            else:
                super(Company.NotFound, self).__init__()

    class AlreadyExists(Exception):
        def __init__(self, name):
            super(Company.AlreadyExists, self).__init__(f"Company:{name} already exists")

    class MissingStripeSetupIntent(Exception):
        def __init__(self, company: 'Company'):
            super(Company.MissingStripeSetupIntent, self).__init__(f"Company {company} missing stripe setup intent")


CompanyTypes = Union[CompanyId, CompanyName, Company]


class CompanyContactOrder(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey('account.User', on_delete=models.CASCADE)
    sort_order = models.IntegerField(null=False, blank=False, default=0)


auditlog.register(Company)


class CompanyJoinRequest(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    requester = models.ForeignKey('account.User', on_delete=models.CASCADE,
                                  related_name='join_request_requester')
    approver = models.ForeignKey('account.User', on_delete=models.CASCADE,
                                 related_name='join_request_approver')

    class CompanyJoinRequestStatus(models.TextChoices):
        PENDING = ('pending', 'Pending')
        APPROVED = ('approved', 'Approved')
        REJECTED = ('rejected', 'Rejected')

    status = models.CharField(choices=CompanyJoinRequestStatus.choices, max_length=60)


auditlog.register(CompanyJoinRequest)
