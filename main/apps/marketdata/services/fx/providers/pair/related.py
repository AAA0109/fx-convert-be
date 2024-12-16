import itertools
import re
from typing import List, Tuple, Dict

from main.apps.core.models import Config
from main.apps.currency.models import FxPair
from main.apps.marketdata.models import FxSpot


class FxSpotPairProvider(object):
    """
    A provider class for retrieving currency pair IDs in FX (foreign exchange) spot trading.
    It extends the CurrencyPairIdProvider class functionality by filtering and storing
    currency pair IDs based on given currencies and a specified mode.

    The 'mode' parameter determines the preference for fetching currency pairs: whether
    to fetch pairs with the specified currency as the base currency, as the quote currency,
    or as either.

    Attributes:
        currencies (List[str]): A list of currency codes that we consider as home currencies.
        mode (str): The mode specifying the preference in currency pair retrieval.
                    - 'base': Fetch pairs where the specified currencies are the base currency.
                    - 'quote': Fetch pairs where the specified currencies are the quote currency.
                    - Any other value: Fetch pairs where the specified currencies are either base or quote.
        _all_pair_ids (dict): A dictionary mapping each currency to its relevant pair IDs.

    Methods:
        retrieve_pair_ids_by_currency(currency: str) -> List[int]:
            Retrieves a list of pair IDs associated with the given currency based on the set mode.

    """
    _currencies: List[str]
    _mode: str
    _all_pair_ids: Dict[str, List[int]]

    def __init__(self, currencies: List[str], mode: str = "quote"):
        if not isinstance(currencies, list):
            raise TypeError("The 'currencies' parameter must be a list")

        self._currencies = currencies
        self._mode = mode
        unique_pairs = FxSpot.objects.values_list('pair', flat=True).distinct()
        fxpairs = {FxPair.get_pair(i).name: FxPair.get_pair(i) for i in unique_pairs}

        self._all_pair_ids = {}
        currencies_to_ignore = []
        for curr in self._currencies:
            if self._mode == "base":
                # Regex pattern for base currency (currency at the start)
                pattern = re.compile(f"^{curr}/")
            elif self._mode == "quote":
                # Regex pattern for quote currency (currency at the end)
                pattern = re.compile(f"/{curr}$")
            else:
                # Regex pattern for any occurrence of the currency
                pattern = re.compile(f"{curr}")

            ignore_pattern = None
            if currencies_to_ignore:
                ignore_pattern = re.compile("|".join(currencies_to_ignore))

            # Filter the pairs, excluding any that match the ignore pattern
            pair_ids = []
            for name, pair in fxpairs.items():
                if re.search(pattern, name):
                    if ignore_pattern and re.search(ignore_pattern, name):
                        continue
                    if name not in pair_ids:
                        pair_ids.append(pair.id)

            self._all_pair_ids[curr] = pair_ids
            currencies_to_ignore.append(curr)

    def retrieve_pair_ids_by_currency(self, currency: str) -> List[int]:
        """
        Retrieves a list of pair IDs associated with the given currency based on the mode.

        Depending on the mode set during initialization, this method filters and returns
        currency pairs where the specified currency is either the base or the quote currency,
        or both.

        Args:
            currency (str): The currency code for which pair IDs are to be retrieved.

        Returns:
            List[int]: A list of currency pair IDs associated with the given currency,
                       filtered based on the mode.
        """
        return self._all_pair_ids[currency]

    @property
    def currencies(self):
        return self._currencies


class CovarianceFxPairProvider(object):
    """
    A provider class for calculating the covariance of FX (foreign exchange) pairs.
    It utilizes an instance of FxSpotPairProvider to retrieve currency pair IDs and
    computes combinations for covariance analysis.

    This class reads configuration settings to determine supported currencies and
    generates all possible pair combinations for these currencies to be used in
    covariance calculations.

    Attributes:
        covar_pairs (List[Tuple[int, int]]): A list of tuples where each tuple contains
                                             a pair of currency IDs for covariance calculation.

    Methods:
        get_ids() -> List[Tuple[int, int]]:
            Returns the list of currency ID pairs for covariance analysis.
    """
    HOME_CURRENCIES_PATH = "system/fxpair/home_currencies"
    TRIANGULATION_CURRENCIES_PATH = "system/fxpair/triangulation_currencies"
    FX_PAIR_ID_PROVIDER_MODE_PATH = "system/fxpair/id_provider/mode"

    def get_covariance_pair_ids(self) -> List[Tuple[int, int]]:
        home_currencies = Config.get_config(path=self.HOME_CURRENCIES_PATH).value
        triangulation_currencies = Config.get_config(path=self.TRIANGULATION_CURRENCIES_PATH).value
        mode = Config.get_config(path=self.FX_PAIR_ID_PROVIDER_MODE_PATH).value
        currencies = home_currencies + triangulation_currencies

        provider = FxSpotPairProvider(currencies=currencies, mode=mode)
        covar_pairs = []
        for c in provider.currencies:
            combination = list(itertools.product(provider.retrieve_pair_ids_by_currency(c), repeat=2))
            covar_pairs.extend(combination)
        return covar_pairs
