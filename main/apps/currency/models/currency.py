from auditlog.registry import auditlog
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from main.apps.util import get_or_none, ActionStatus

from typing import List, Iterable, Union, Sequence, Optional, Tuple

from hdlib.Core.Currency import Currency as CurrencyHDL

import logging

logger = logging.getLogger(__name__)

# =====================================
# Type Definitions
# =====================================

CurrencyId = int
CurrencyMnemonic = str  # e.g. "USD"


class Currency(models.Model, CurrencyHDL):
    class Meta:
        verbose_name_plural = "currencies"
        ordering = ['mnemonic']

    symbol = models.CharField(max_length=10, null=True)

    class SymbolLocation(models.TextChoices):
        PREFIX = "prefix", _("Prefix")
        SUFFIX = "suffix", _("Suffix")

    symbol_location = models.CharField(max_length=6, choices=SymbolLocation.choices, default=SymbolLocation.PREFIX)
    mnemonic = models.CharField(max_length=3, null=False, unique=True)
    name = models.CharField(max_length=255, null=True)
    unit = models.IntegerField(null=True, blank=True)
    numeric_code = models.CharField(max_length=255, null=True, unique=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    image_thumbnail = models.ImageField(
        upload_to="currency/thumbnail/", blank=True, null=True)
    image_banner = models.ImageField(
        upload_to="currency/banner/", blank=True, null=True)

    # TODO: This should be moved to FX Pair
    class CurrencyCategory(models.TextChoices):
        P10 = 'p10', _('P10')
        OTHER = 'other', _('Other')
        ALL = 'all', _('All')

    category = models.TextField(max_length=10, choices=CurrencyCategory.choices, null=True)

    # =============================================================
    #  Currency (i.e. CurrencyHDL) methods.
    # =============================================================

    def get_name(self) -> str:
        """ Full Display name of currency, e.g. US Dollars """
        return self.name

    def get_mnemonic(self) -> str:
        """ The three character mnemonic, e.g. USD """
        return self.mnemonic

    def get_thumbnail_url(self) -> str:
        """ The url of a thubnail image, e.g. /media/currency/thumbnail/usa.webp """
        return self.image_thumbnail.url

    def get_banner_url(self) -> str:
        """ The url of a banner image, e.g. /media/currency/banner/usa.webp """
        return self.image_banner.url

    def __hash__(self):
        """ Need to override __hash__ since both model and FxPairInterface implement this. """
        return hash(self.get_mnemonic())

    def __repr__(self):
        """ Need to override __repr__ since both model and FxPairInterface implement this. """
        return self.get_mnemonic()

    def __str__(self):
        """ Need to override __str__ since both model and FxPairInterface implement this. """
        return self.get_mnemonic()

    # ============================
    # Accessors
    # ============================

    @staticmethod
    @get_or_none
    def get_currency(currency: Union[CurrencyId, CurrencyMnemonic, CurrencyHDL, 'Currency']) -> Optional['Currency']:
        """
        Get a currency object.
        :param currency: int, str, CurrencyHDL, or Currency. If int, this is the currency id. If str, this is the
            currency mnemonic. If CurrencyHDL, does lookup based on mnemonic. If already Currency, return as is.
        :return: Currency, the matching currency if found, else None
        """
        if isinstance(currency, CurrencyId):
            return Currency.objects.get(id=currency)
        if isinstance(currency, CurrencyMnemonic):
            return Currency.objects.get(mnemonic=currency.upper())
        if isinstance(currency, CurrencyHDL):
            return Currency.objects.get(mnemonic=currency.get_mnemonic())
        if isinstance(currency, Currency):
            return currency
        return None

    @staticmethod
    def get_currencies(ids: Iterable[CurrencyId] = None,
                       mnemonics: Iterable[CurrencyMnemonic] = None) -> Sequence['Currency']:
        """
        Get currencies by id or mnemonic. If neither supplied, get all currencies
        :param ids: Iterable of str or int, the primary keys
        :param mnemonics: Iterable of str, the 3 char mnemonics, e.g. [USD, GBP]
        :return: Sequence of currencies found
        """
        if ids:
            return Currency.objects.filter(id__in=ids)
        if mnemonics:
            return Currency.objects.filter(mnemonic__in=mnemonics)
        return Currency.objects.all()

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def create_currency(mnemonic: str,
                        name: Optional[str] = None,
                        symbol: Optional[str] = None) -> Tuple[ActionStatus, Optional['Currency']]:
        should_update = False
        try:
            currency, created = Currency.objects.get_or_create(mnemonic=mnemonic)
        except IntegrityError as ex:
            return ActionStatus.log_and_no_change(f"A currency named {name} already exists!"), None
        except Exception as ex:
            return ActionStatus.log_and_error(f"Error creating currency"), None
        if not created:
            return ActionStatus.log_and_no_change(f"A currency named {name} already exists!"), currency
        if name is not None:
            currency.name = name
            should_update = True
        if symbol is not None:
            currency.symbol = symbol
            should_update = True
        if should_update:
            currency.save()
        return ActionStatus.log_and_success(f"Created currency {name if name else mnemonic}"), currency

    @staticmethod
    def create_currency_from_hdl(currency: CurrencyHDL) -> Tuple[ActionStatus, 'Currency']:
        return Currency.create_currency(mnemonic=currency.get_mnemonic(),
                                        name=currency.get_name(),
                                        symbol=None)

    @staticmethod
    def create_currency_from_cls(cls: type) -> Tuple[ActionStatus, Optional['Currency']]:
        """
        Create a currency from a *type*, e.g. Currency.create_currency_from_cls(USDCurrency)
        """
        try:
            currency = cls()
            return Currency.create_currency(mnemonic=currency.get_mnemonic(),
                                            name=currency.get_name(),
                                            symbol=None)
        except Exception as ex:
            return ActionStatus.log_and_error(f"Currency could not be created, exception: {ex}"), None

    class NotFound(Exception):
        def __init__(self, cny: Union[CurrencyId, CurrencyMnemonic, 'Currency']):
            if isinstance(cny, CurrencyId):
                super(Currency.NotFound, self).__init__(
                    f"Currency with id:{cny} is not found")
            elif isinstance(cny, CurrencyMnemonic):
                super(Currency.NotFound, self).__init__(
                    f"Currency with name:{cny} is not found")
            elif isinstance(cny, Currency):
                super(Currency.NotFound, self).__init__(
                    f"Currency:{cny} is not found")
            else:
                super(Currency.NotFound, self).__init__()

    @staticmethod
    def get_currencies_choices():
        output = []
        for currency in Currency.objects.all():
            output.append((currency.id, currency.mnemonic))
        return output



auditlog.register(Currency)

# Define the set of types that can specify a Currency and be correctly interpreted by the get_currency function.
CurrencyTypes = Union[CurrencyId, CurrencyMnemonic, CurrencyHDL, Currency]
