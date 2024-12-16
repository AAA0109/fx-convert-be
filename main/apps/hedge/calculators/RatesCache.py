from main.apps.broker.models import Broker
from main.apps.currency.models import Currency
from main.apps.hedge.models import TieredRate

from typing import List, Optional, Dict, Iterable, Union

import logging

logger = logging.getLogger(__name__)


class RatesCache:
    """
    Cache for long (interest paid to customer) and short (margin loan) rates for a particular broker.
    """

    def __init__(self,
                 interest_rate_tiers: Dict[Currency, List[TieredRate]],
                 loan_rate_tiers: Dict[Currency, List[TieredRate]],
                 broker: Optional[Broker] = None):
        # TODO: Store reference date?
        self._interest_rates = interest_rate_tiers
        self._loan_rates = loan_rate_tiers
        # Which broker these rates are for.
        self._broker = broker

    @property
    def broker(self) -> Broker:
        return self._broker

    def get_currencies(self) -> Iterable[Currency]:
        return self._interest_rates.keys()

    def has_currency(self, currency: Currency) -> bool:
        return self._interest_rates.get(currency, None) is not None

    def get_loan_rates(self, currency: Currency):
        return self._loan_rates.get(currency, None)

    def get_interest_rates(self, currency: Currency):
        return self._interest_rates.get(currency, None)


class BrokerRatesCaches:
    def __init__(self, rates_caches: Dict[str, RatesCache] = None):
        self._rates_caches = rates_caches or {}

    def get_cache(self, broker: Union[Broker, str]) -> Optional[RatesCache]:
        name = broker.name if isinstance(broker, Broker) else broker
        return self._rates_caches.get(name, None)

    def add_cache(self, rates_cache: RatesCache):
        if not rates_cache.broker:
            raise ValueError("Your rates cache must have the broker attribute")
        self._rates_caches[rates_cache.broker.name] = rates_cache
