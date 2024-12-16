from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.Hedge.Fx.HedgeCostProvider import HedgeCostProvider
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.broker.models import BrokerTypes, Broker
from main.apps.currency.models import FxPair, Currency
from main.apps.hedge.models import InterestRate, TieredRate
from main.apps.hedge.models.cost import FxSpotCommission, FxSpotSpread
from main.apps.hedge.models.margin import CurrencyMargin
from main.apps.margin.models.margin import FxSpotMargin
from main.apps.hedge.calculators.cost import StandardRollCostCalculator
from main.apps.hedge.calculators.RatesCache import RatesCache, BrokerRatesCaches

from typing import List, Optional, Sequence, Tuple, Dict, Union, Iterable
import pandas as pd
import numpy as np

import logging

logger = logging.getLogger(__name__)

FxName = str


def _add_dictionaries(m1, m2):
    out = {}
    for key in set(m1.keys()).union(set(m2.keys())):
        out[key] = m1.get(key, 0) + m2.get(key, 0)
    return out


class CostCache(HedgeCostProvider):
    def __init__(self,
                 commission: Dict[FxPairInterface, float],
                 spreads: Dict[FxPairInterface, float],
                 spot_margin_rates: Dict[FxPairInterface, float],
                 long_spot_roll_rates: Dict[FxPairInterface, float],
                 short_spot_roll_rates: Dict[FxPairInterface, float]
                 ):
        self._commission = self._make_series(commission)
        self._spreads = self._make_series(spreads)
        self._spot_margin_rates = self._make_series(spot_margin_rates)
        self._long_spot_roll_rates = self._make_series(long_spot_roll_rates)
        self._short_spot_roll_rates = self._make_series(short_spot_roll_rates)

        self._costs = self._make_series(_add_dictionaries(commission, spreads))

    def get_spot_fx_transaction_costs(self,
                                      date: Date,
                                      fx_pairs: Optional[Sequence[FxPairInterface]] = None) -> pd.Series:
        if fx_pairs is None:
            return self._costs
        # We assume that the cost is symmetric between XXX/YYY and YYY/XXX, b/c in reality only one is tradeable,
        # which is where the cost is derived from.
        return self._get_symmetric_rates(all_rates=self._costs, fx_pairs=fx_pairs)

    def get_spot_fx_margin_rates(self,
                                 date: Date,
                                 fx_pairs: Optional[Sequence[FxPairInterface]] = None) -> pd.Series:
        if fx_pairs is None:
            return self._spot_margin_rates
        return self._get_symmetric_rates(all_rates=self._spot_margin_rates, fx_pairs=fx_pairs)

    def get_spot_fx_roll_rates(self,
                               date: Date,
                               fx_pairs: Optional[Sequence[FxName]] = None) -> Tuple[pd.Series, pd.Series]:
        if fx_pairs is None:
            return self._long_spot_roll_rates, self._short_spot_roll_rates
        long_rates = pd.Series(index=fx_pairs, dtype=float)
        short_rates = pd.Series(index=fx_pairs, dtype=float)

        for i in range(len(fx_pairs)):
            long_rates.iloc[i] = self._long_spot_roll_rates.get(fx_pairs[i], np.nan)
            short_rates.iloc[i] = self._long_spot_roll_rates.get(fx_pairs[i], np.nan)

        return long_rates, short_rates

    @staticmethod
    def _make_series(dictionary: dict):
        return pd.Series(index=[fx_pair for fx_pair in dictionary.keys()], data=dictionary.values(), dtype=float)

    def _get_symmetric_rates(self, all_rates: pd.Series, fx_pairs: Sequence[FxPairInterface]):
        """
        Helper to get a set of rates in the case where they are symmetric between XXX/YYY and YYY/XXX,
        e.g. spot margin rates
        """
        rates = pd.Series(index=fx_pairs, dtype=float)
        for i in range(len(rates)):
            rate = all_rates.get(fx_pairs[i], None)
            if rate is None:
                rate = all_rates.get(fx_pairs[i].make_inverse(), np.nan)
            rates.iloc[i] = rate
        return rates


class CostProviderService:
    """
    Service used to create cost providers
    """

    def get_cost_provider(self,
                          date: Date,
                          fx_cache: SpotFxCache,
                          fx_pairs: Optional[Sequence[FxPair]] = None,
                          domestic: Optional[Currency] = None,
                          broker: Optional[BrokerTypes] = "IBKR",
                          rates_cache: Optional[RatesCache] = None) -> HedgeCostProvider:

        # Get the hedge cost provider
        broker = Broker.get_broker(broker)
        date = Date.to_date(date)

        try:
            commissions, _ = FxSpotCommission.get_rates(date=date, broker=broker, fx_pairs=fx_pairs)
        except Exception as e:
            logger.error(f"Error getting commision rates, will be missing in cost provider: {e}")
            commissions = {}

        try:
            spreads, _ = FxSpotSpread.get_spreads(date=date, broker=broker, fx_pairs=fx_pairs)
        except Exception as e:
            logger.error(f"Error getting spot spreads, will be missing in cost provider: {e}")
            spreads = {}

        try:
            spot_margin_rates, _ = FxSpotMargin.get_rates(date=date, broker=broker, fx_pairs=fx_pairs)
        except Exception as e:
            logger.error(f"Error getting spot margin rates, will be missing in cost provider: {e}")
            spot_margin_rates = {}

        try:
            rates_cache = rates_cache if rates_cache else self.create_rates_cache(broker=broker, time=date)
            cost_calc = StandardRollCostCalculator()
            long_roll_rates, short_roll_rates = cost_calc.get_roll_rates_for_fx_positions(
                fx_pairs=fx_pairs, start_date=date, end_date=date + 1, dc=DayCounter_HD(),
                spot_fx_cache=fx_cache, rates_cache=rates_cache, domestic=domestic
            )

        except Exception as e:
            logger.error(f"Error getting roll rates, will be missing in cost provider: {e}")
            long_roll_rates, short_roll_rates = {}, {}

        return CostCache(commission=commissions,
                         spreads=spreads,
                         spot_margin_rates=spot_margin_rates,
                         long_spot_roll_rates=long_roll_rates,
                         short_spot_roll_rates=short_roll_rates)

    def create_rates_cache(self,
                           time: Date,
                           broker: Optional[BrokerTypes] = "IBKR",
                           window: int = 5) -> RatesCache:
        broker_ = Broker.get_broker(broker)
        if not broker_:
            raise ValueError(f"could not find broker {broker}")

        time = Date.to_date(time)
        time_start = time - window

        filters = {'broker': broker_,
                   'date__lte': time,
                   'date__gte': time_start}

        interest_rates = list(InterestRate.objects.filter(**filters).order_by("-date", "tier_from"))
        loan_rates = list(CurrencyMargin.objects.filter(**filters).order_by("-date", "tier_from"))
        # Convert into dictionaries from currency to tiers, and add them to cache.
        return RatesCache(loan_rate_tiers=self._convert_tiers(loan_rates),
                          interest_rate_tiers=self._convert_tiers(interest_rates),
                          broker=broker_)

    def create_all_rates_caches(self,
                                time: Date,
                                brokers: Iterable[Broker] = None,
                                window: int = 5) -> BrokerRatesCaches:
        caches = BrokerRatesCaches()

        for broker in brokers:
            caches.add_cache(rates_cache=self.create_rates_cache(time=time, broker=broker, window=window))

        return caches

    def _convert_tiers(self, tiered_rates):
        output = {}
        for rate in tiered_rates:
            currency = rate.currency
            if currency not in output:
                output[currency] = []
            output[currency].append(rate)
        return output


