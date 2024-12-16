import logging
from typing import Iterable, Iterator, Union, Sequence, Tuple, Optional

from auditlog.registry import auditlog
from django.core.cache import cache
from django.db import models
from django.db.models import Q, Prefetch
from hdlib.Core.Currency import Currency as CurrencyHDL
from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Core.FxPairInterface import FxPairInterface

from main.apps.core.utils.cache import redis_func_cache
from main.apps.currency.models import Currency, CurrencyMnemonic, CurrencyTypes
from main.apps.util import get_or_none, ActionStatus

logger = logging.getLogger(__name__)

# =====================================
# Type Definitions
# =====================================
FxPairId = int  # Type to represent the primary key for an fx pair
FxPairName = str  # Type to represent the name of an fx pair, internal convention: "USD/GBP"


class FxPair(models.Model, FxPairInterface):
    class Meta:
        verbose_name_plural = "FX Pairs"
        unique_together = (("base_currency", "quote_currency"),)
        ordering = ['base_currency__mnemonic', 'quote_currency__mnemonic']

    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='base_currency', null=False)
    quote_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='quote_currency', null=False)

    # =============================================================
    #  FxPairInterface methods.
    # =============================================================

    def get_base_currency(self) -> Currency:
        """ Get the base currency of this FxPair. """
        return self.base_currency

    def get_quote_currency(self) -> Currency:
        """ Get the quote currency of this FxPair. """
        return self.quote_currency

    def make_inverse(self) -> 'FxPair':
        """ Get the inverse pair of this pair. """
        return self.get_inverse_pair(self)

    @property
    def market(self) -> str:
        """ Get the market of this fx pair. Because who uses / in their fx names? """
        return f"{self.base.get_mnemonic()}{self.quote.get_mnemonic()}"

    _name = None

    @property
    def name(self):
        """Had to override this to enable this this qs override to work:
        main.apps.currency.admin.FxPairAdmin.get_queryset"""
        if self._name is not None:
            return self._name
        self._name = f"{self.base.get_mnemonic()}/{self.quote.get_mnemonic()}"
        return self._name

    @name.setter
    def name(self, value):
        """Had to override this to enable this this qs override to work:
        main.apps.currency.admin.FxPairAdmin.get_queryset"""
        self._name = value

    def __hash__(self):
        """ Need to override __hash__ since both model and FxPairInterface implement this. """
        return hash(self.name)

    def __repr__(self):
        """ Need to override __repr__ since both model and FxPairInterface implement this. """
        return self.name

    def __str__(self):
        """ Need to override __str__ since both model and FxPairInterface implement this. """
        return self.name

    # =============================================================
    #  Other methods.
    # =============================================================

    def to_FxPairHDL(self) -> FxPairHDL:
        """ Get an hdlib representation of the object """
        return FxPairHDL(base=self.base_currency, quote=self.quote_currency)

    def __lt__(self, rhs: 'FxPair'):
        # TODO(Nate): Do we really need this?
        return self.__str__() < str(rhs)

    # Fx Pair types to identify a pair
    Types = Union[FxPairId, FxPairName, 'FxPair', FxPairHDL]

    # ============================
    # Accessors
    # ============================

    @staticmethod
    @redis_func_cache(key=None, timeout=60 * 60 * 20, delete=False)
    def get_all_pairs():
        return FxPair.get_pairs()

    @staticmethod
    def get_pairs(pair_ids: Iterable[int] = None,
                  except_these: bool = False,
                  with_data: bool = True) -> Sequence['FxPair']:
        """
        Get fx pairs. Note that the order of pairs return won't match the pair ids supplied
        :param pair_ids: Iterable of pair ids, if not supplied return all pairs
        :param except_these: bool, if true, then treat the supplied pairs as those NOT to retrive (ie retrieve
            all pairs except_these). Else it retrieves only these pairs
        :param with_data: If this is enabled we will only fetch pairs with data
        :return: Fx pairs (not in same order as supplied ids)
        """
        from main.apps.marketdata.models import FxSpot, FxForward, FxPair

        qs = FxPair.objects.prefetch_related(
            Prefetch('base_currency'),
            Prefetch('quote_currency')
        )

        if with_data:
            cache_key = 'fx_pair_ids_with_data'
            pair_ids = cache.get(cache_key)

            if pair_ids is None:
                spot_pairs = FxSpot.objects.values_list('pair', flat=True).distinct()
                forward_pairs = FxForward.objects.values_list('pair', flat=True).distinct()
                pair_ids = set(list(spot_pairs) + list(forward_pairs))
                cache.set(cache_key, pair_ids, timeout=600)

        if pair_ids is not None:
            if except_these:
                qs = qs.exclude(id__in=pair_ids)
            else:
                qs = qs.filter(id__in=pair_ids)

        return qs

    @staticmethod
    def get_pairs_by_name(fx_names: Iterable[str]) -> Iterator['FxPair']:
        # Assuming fx_names is a list of strings like ["EUR/USD", "GBP/USD", ...]

        # Initialize an empty Q object
        query = Q()

        # Iterate over fx_names and construct OR conditions
        for pair in fx_names:
            base_currency, quote_currency = pair.split('/')
            query |= Q(base_currency__mnemonic=base_currency, quote_currency__mnemonic=quote_currency)

        # Query FxPair instances using the constructed query
        pairs = FxPair.objects.filter(query)

        return pairs.iterator()

    @staticmethod
    @get_or_none
    def get_pair(pair: Types) -> Optional['FxPair']:
        """
        Get an FxPair by Id or other attributes
        :param pair: FxPair, the id or other uniquely identifying attributes
        :return: FxPair if found, else None
        """
        qs = FxPair.objects.select_related('base_currency', 'quote_currency')
        if isinstance(pair, FxPair):
            return pair
        if isinstance(pair, FxPairId):
            return qs.get(id=pair)
        if isinstance(pair, FxPairName):
            if len(pair) == 6:  # "EURUSD"
                return qs.get(base_currency__mnemonic=pair[:3], quote_currency__mnemonic=pair[3:])
            else:  # Like "EUR/USD"
                return qs.get(base_currency__mnemonic=pair[:3], quote_currency__mnemonic=pair[4:])
        if isinstance(pair, FxPairHDL):
            return qs.get(base_currency__mnemonic=pair.base.get_mnemonic(),
                          quote_currency__mnemonic=pair.quote.get_mnemonic())
        if isinstance(pair, tuple):
            base: CurrencyHDL = pair[0]
            quote: CurrencyHDL = pair[1]
            return qs.get(base_currency__mnemonic=base.get_mnemonic(),
                          quote_currency__mnemonic=quote.get_mnemonic())
        return None

    @staticmethod
    @get_or_none
    def get_pair_from_currency(base_currency: CurrencyHDL, quote_currency: CurrencyHDL) -> 'FxPair':
        return FxPair.get_pair(f"{base_currency}/{quote_currency}")

    @staticmethod
    @get_or_none
    def get_inverse_pair(pair: Types) -> Optional['FxPair']:
        pair_ = FxPair.get_pair(pair)
        if not pair_:
            return None
        return FxPair.get_pair(pair_.inverse_name)

    @staticmethod
    @get_or_none
    def get_inverse_from_fxpairinterface(pair: FxPairInterface):
        return FxPair.get_pair(pair.inverse_name)

    @staticmethod
    def get_foreign_to_domestic_pairs(domestic: CurrencyTypes,
                                      foreign_ids: Iterable[CurrencyTypes] = None,
                                      foreign_names: Iterable[CurrencyMnemonic] = None) -> Sequence['FxPair']:
        """
        Get all pairs between a set of foreign ids and a single domestic id, of the form "Foreign/Domestic"
        :param domestic: domestic currency id or object)
        :param foreign_ids: foreign currency ids (or currency objects), must supply this or foreign_names
        :param foreign_names: foreign currency mnemonics, must supply this or foreign_ids
        :return: Sequence of FxPairs
        """
        domestic_ = Currency.get_currency(domestic)
        if not domestic_:
            raise ValueError(f"The supplied domestic currency couldn't be found: {domestic}")
        if foreign_ids:
            return FxPair.objects.filter(quote_currency=domestic_, base_currency__in=foreign_ids)
        if not foreign_names:
            return FxPair.objects.filter(quote_currency=domestic_).exclude(base_currency=domestic_)
        return FxPair.objects.filter(quote_currency=domestic_, base_currency__mnemonic__in=foreign_names)

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def create_fxpair(base: CurrencyTypes, quote: CurrencyTypes) -> Tuple[ActionStatus, Optional['FxPair']]:
        base_curr = Currency.get_currency(base)
        quote_curr = Currency.get_currency(quote)

        if quote_curr is None:
            return ActionStatus.log_and_error(f"Could not get quote currency {quote}"), None
        if base_curr is None:
            return ActionStatus.log_and_error(f"Could not get base currency {base}"), None

        try:
            fxpair, created = FxPair.objects.get_or_create(base_currency=base_curr, quote_currency=quote_curr)
        except Exception as ex:
            return ActionStatus.log_and_error(f"Error creating FxPair: {ex}"), None
        if not created:
            return ActionStatus.log_and_no_change(f"Did not create fx pair {base}/{quote}"), fxpair

        return ActionStatus.log_and_success(f"Created fxpair {base}/{quote}"), fxpair

    @staticmethod
    def create_reverse_pair(fx_pair: Types) -> Tuple[ActionStatus, Optional['FxPair']]:
        """
        Create a reverse FxPair for an existing Fx Pair. If he supplied pair doesnt exist, no reverse will be created
        If the reverse already exists, the ActionStatus will indicate that.
        :param fx_pair: FxPair unique identifier
        :return: ActionStatus (indicating what happened) and the FxPair, if it was created or already existed
        """
        fx_pair = FxPair.get_pair(pair=fx_pair)
        if not fx_pair:
            return ActionStatus.log_and_error("Could not find the supplied pair, you're trying to create a reverse"), \
                None

        try:
            reverse, created = FxPair.objects.get_or_create(
                base_currency=fx_pair.quote_currency,
                quote_currency=fx_pair.base_currency)
            if created:
                return ActionStatus.log_and_success(f"Succesfully created new pair: {reverse}"), reverse
            return ActionStatus.log_and_no_change(f"Reverse pair already exists: {reverse}"), reverse
        except Exception as e:
            return ActionStatus.log_and_error(f"Unkown Error creating the reverse pair: {e}"), None

    @staticmethod
    def get_pairs_by_base_quote_currency(currency: str = 'USD'):
        return FxPair.objects.filter(Q(base_currency__mnemonic=currency) | Q(quote_currency__mnemonic=currency))


auditlog.register(FxPair)


class FxPairMeta:
    pair = models.ForeignKey(FxPair, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


# Define the set of types that can specify and FxPair and be correctly interpreted by the get_pair function.
FxPairTypes = FxPair.Types
