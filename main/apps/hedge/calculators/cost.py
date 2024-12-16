import abc
from abc import ABC
from typing import Sequence, Iterable, Tuple, Dict, Optional
import numpy as np

from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.DateTime.DayCounter import DayCounter
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.DateTime import Date

from main.apps.currency.models.fxpair import FxPair
from main.apps.currency.models import Currency
from main.apps.hedge.models import TieredRate
from main.apps.hedge.calculators.RatesCache import RatesCache

import logging

logger = logging.getLogger(__name__)


class RollCostCalculator(ABC):

    @abc.abstractmethod
    def get_interest(self,
                     amount: float,
                     start_date: Date,
                     end_date: Date,
                     dc: DayCounter,
                     currency: Currency,
                     rates_cache: RatesCache) -> float:
        """
        Get the interst in units of the currency in which deposit (loan) is made. If interest is earned, the result
        is positive. Else its negative
        :param amount: float, the amount deposited (positive) or borrowed (negative), in units of currency
        :param start_date: Date, the start date of the calculation
        :param end_date: Date, the end date of the calculation
        :param dc: DayCounter, determines how many days are charged / earned interest, and whether it is inclusive
            of start/end date
        :param currency: Currency, the currency in which interest is earned / paid
        :param rates_cache: RatesCache, contains interest/loan rates
        :return: float, the interest earned (positive) or paid (negative)
        """
        raise NotImplementedError

    def get_interest_in_domestic(self,
                                 domestic: Currency,
                                 cash_currency: Currency,
                                 amount: float,
                                 start_date: Date,
                                 end_date: Date,
                                 dc: DayCounter,
                                 spot_fx_cache: SpotFxCache,
                                 rates_cache: RatesCache) -> float:
        """
        Calculate the interest earned/paid for single cash position, converted into units of some domestic currency
        :param domestic: Currency, the currency in which to convert the interest earned/paid at the spot fx rate
        :param cash_currency: Currency, the currency in which interest is earned / paid
        :param amount: float, the amount deposited (positive) or borrowed (negative), in units of cash_currency
        :param start_date: Date, the start date of the calculation
        :param end_date: Date, the end date of the calculation
        :param dc: DayCounter, determines how many days are charged / earned interest, and whether it is inclusive
                of start/end date
        :param spot_fx_cache: SpotFxCache, cache of the spot fx rates
        :param rates_cache: RatesCache, contains interest/loan rates
        :return: float, the interest earned (positive) or paid (negative), in units of domestic currency
        """
        value = self.get_interest(amount=amount,
                                  start_date=start_date,
                                  end_date=end_date,
                                  dc=dc,
                                  currency=cash_currency,
                                  rates_cache=rates_cache)
        return spot_fx_cache.convert_value(from_currency=cash_currency, to_currency=domestic, value=value)

    def get_roll_rates_for_fx_position(self,
                                       start_date: Date,
                                       end_date: Date,
                                       dc: DayCounter,
                                       fx_pair: FxPairInterface,
                                       fx_spot: float,
                                       rates_cache: RatesCache) -> Tuple[Optional[float], Optional[float]]:
        """
        Get the roll cost, as a rate PER UNIT of an FX position, both LONG and SHORT.

        NOTE: POSITVE roll rate = interested earned, NEGATIVE roll rate = interest paid
        Generally, due to the broker spread, we expect to pay interest on BOTH the long and short position
        :param start_date: Date, the start date of the calculation
        :param end_date: Date, the end date of the calculation
        :param dc: DayCounter, determines how many days are charged / earned interest, and whether it is inclusive
                of start/end date
        :param fx_pair: FxPairInterface, the pair held
        :param fx_spot: float, the fx spot rate for this fx_pair
        :param rates_cache: RatesCache, contains interest/loan rates
        :return: Tuple, (long roll_cost, short roll_cost)
        """
        # Long Rate (rate per long unit holding of this fx pair)
        interest_long = self.get_interest(amount=1., start_date=start_date, end_date=end_date, dc=dc,
                                          currency=fx_pair.get_base_currency(),
                                          rates_cache=rates_cache)
        if interest_long is None:
            return None, None

        interest_long *= fx_spot  # Convert into the quote currency
        interest_short = self.get_interest(amount=-fx_spot, start_date=start_date, end_date=end_date, dc=dc,
                                           currency=fx_pair.get_quote_currency(),
                                           rates_cache=rates_cache)
        if interest_short is None:
            return None, None
        # To get the rate on the long position (which is rate PER unit of this FX pair holding),
        # sum the interest recieved on the long position, and the interest paid on the short position
        long_rate = interest_long + interest_short

        # Short Rate (rate per short unit holding of this fx pair)
        interest_short = self.get_interest(amount=-1., start_date=start_date, end_date=end_date, dc=dc,
                                           currency=fx_pair.get_base_currency(),
                                           rates_cache=rates_cache)
        interest_short *= fx_spot  # Convert into the quote currency

        interest_long = self.get_interest(amount=fx_spot, start_date=start_date, end_date=end_date, dc=dc,
                                          currency=fx_pair.get_quote_currency(),
                                          rates_cache=rates_cache)
        short_rate = interest_long + interest_short

        return long_rate, short_rate

    def get_roll_cost_for_fx_position(self,
                                      start_date: Date,
                                      end_date: Date,
                                      dc: DayCounter,
                                      fx_pair: FxPairInterface,
                                      fx_spot: float,
                                      rates_cache: RatesCache,
                                      amount: float) -> float:
        """
        Get the roll cost for an amount of fx position

        NOTE: POSITVE roll rate = interested earned, NEGATIVE roll rate = interest paid
        Generally, due to the broker spread, we expect to pay interest on BOTH the long and short position
        :param start_date: Date, the start date of the calculation
        :param end_date: Date, the end date of the calculation
        :param dc: DayCounter, determines how many days are charged / earned interest, and whether it is inclusive
                of start/end date
        :param fx_pair: FxPairInterface, the pair held
        :param fx_spot: float, the fx spot rate for this fx_pair
        :param rates_cache: RatesCache, contains interest/loan rates
        :param amount: float, the amount of fx position held (positive for long position, negative for short)
        :return: float, the roll cost for this amount of fx position
        """
        rate_long, rate_short = self.get_roll_rates_for_fx_position(start_date=start_date, end_date=end_date, dc=dc,
                                                                    fx_pair=fx_pair, fx_spot=fx_spot,
                                                                    rates_cache=rates_cache)
        if amount > 0:
            return amount * rate_long

        return abs(amount) * rate_short

    def get_roll_rates_for_fx_positions(self,
                                        start_date: Date,
                                        end_date: Date,
                                        dc: DayCounter,
                                        spot_fx_cache: SpotFxCache,
                                        rates_cache: RatesCache,
                                        fx_pairs: Optional[Iterable[FxPairInterface]] = None,
                                        domestic: Optional[Currency] = None
                                        ) -> Tuple[Dict[FxPairInterface, float], Dict[FxPairInterface, float]]:
        """
        Calculate the roll rates per unit of fx pair holding, long and short
        NOTE: POSITIVE roll rate = interested earned, NEGATIVE roll rate = interest paid
        Generally, due to the broker spread, we expect to pay interest on BOTH the long and short position
        """
        if not domestic and fx_pairs is None:
            raise ValueError("You must supply either domestic currency or Fx pairs to get roll costs")

        if fx_pairs is None:
            fx_pairs_ = FxPair.get_foreign_to_domestic_pairs(domestic=domestic)
        else:
            fx_pairs_: Iterable[FxPairInterface] = fx_pairs

        long_rates, short_rates = {}, {}
        for pair in fx_pairs_:
            if not rates_cache.has_currency(currency=pair.get_base_currency()) \
                or not rates_cache.has_currency(currency=pair.get_quote_currency()):
                continue
            fx_spot = spot_fx_cache.get_fx(fx_pair=pair, value_if_missing=None)
            if fx_spot is None:
                continue
            try:
                long_rate, short_rate = self.get_roll_rates_for_fx_position(
                    start_date=start_date, end_date=end_date, dc=dc,
                    fx_pair=pair, fx_spot=fx_spot,
                    rates_cache=rates_cache)
                if long_rate is None or short_rate is None:
                    continue
                long_rates[pair] = long_rate
                short_rates[pair] = short_rate
            except Exception as e:
                logger.warning(f"Error retriving roll rate for pair {pair.name}: {e}")
                continue

        return long_rates, short_rates

    def get_roll_cost_for_cash_positions(self,
                                         start_date: Date,
                                         end_date: Date,
                                         dc: DayCounter,
                                         spot_fx_cache: SpotFxCache,
                                         domestic: Currency,
                                         rates_cache: RatesCache,
                                         positions: CashPositions
                                         ) -> float:
        total_cost = 0
        for currency, amount in positions.cash_by_currency.items():
            total_cost += self.get_interest_in_domestic(domestic=domestic,
                                                        cash_currency=currency,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        dc=dc,
                                                        spot_fx_cache=spot_fx_cache,
                                                        rates_cache=rates_cache,
                                                        amount=amount)
        return total_cost


class StandardRollCostCalculator(RollCostCalculator):
    # ============================
    # Roll Cost Methods
    # ============================

    def get_interest(self,
                     amount: float,
                     start_date: Date,
                     end_date: Date,
                     dc: DayCounter,
                     currency: Currency,
                     rates_cache: RatesCache) -> float:
        if amount < 0:  # Money loaned to company.
            tiered_rates = rates_cache.get_loan_rates(currency)
        else:  # Money deposited by company.
            tiered_rates = rates_cache.get_interest_rates(currency)
        if not tiered_rates:
            raise ValueError(f"could not find currency {currency} in the appropriate rates type")
        return self._get_interest_from_tiers(amount=amount,
                                             start_date=start_date,
                                             end_date=end_date,
                                             dc=dc,
                                             tiered_rates=tiered_rates)

    # =====================================================
    #  Private helper functions.
    # =====================================================

    def _get_interest_from_tiers(self,
                                 amount: float,
                                 start_date: Date,
                                 end_date: Date,
                                 dc: DayCounter,
                                 tiered_rates: Iterable[TieredRate]):
        # Make sure amount is positive.

        sg = np.sign(amount)
        amount = np.abs(amount)
        last_tier, interest = 0, 0

        ttm = dc.year_fraction(start=start_date, end=end_date)

        for rate in tiered_rates:
            # Note: we allow for the case of Null tier from and tier to (case of only one tier)
            tier_from = rate.tier_from if rate.tier_from is not None else 0
            if tier_from != last_tier:
                raise ValueError("tier mismatch")
            try:
                cap = amount if rate.tier_to is None else np.minimum(rate.tier_to, amount)
            except Exception:
                raise
            # interest += (cap - last_tier) * (np.exp(rate.rate * ttm) - 1.0)
            # TODO: replace with compound interest calc
            interest += (cap - last_tier) * rate.rate * ttm

            if not rate.tier_to or amount < rate.tier_to:
                break
            last_tier = rate.tier_to
        return sg * interest
