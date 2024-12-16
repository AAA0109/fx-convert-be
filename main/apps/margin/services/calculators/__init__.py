from abc import ABC, abstractmethod
from typing import Dict, Tuple
from typing import Iterable

import scipy.optimize
from hdlib.Core.Currency import Currency as CurrencyHDL
from hdlib.Hedge.Cash.CashPositions import CashPositions, VirtualFxPosition
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from main.apps.broker.models import Broker
from main.apps.currency.models import FxPair, Currency


class MarginRatesCache:
    def __init__(self,
                 broker: Broker,
                 default_margin_rate: float = 0.10,
                 spot_fx_cache: SpotFxCache = None,
                 margin: Dict[Tuple[str, str], float] = None):
        self.broker = broker
        self.margin = {} if margin is None else margin
        self.spot_fx_cache = spot_fx_cache
        self.default_margin_rate = default_margin_rate

    def __call__(self, base: CurrencyHDL, quote: CurrencyHDL) -> float:
        """ Get the margin per unit Fx spot for an Fx pair, in domestic. """
        margin_rate = self.margin.get((base.get_mnemonic(), quote.get_mnemonic()), None)
        if not margin_rate:
            return self.default_margin_rate
        return margin_rate.rate

    def get_rate_for_pair(self, fxpair: FxPair) -> float:
        """ Get the margin per unit Fx spot for an Fx pair, in domestic. """
        return self(fxpair.base, fxpair.quote)

    def get_rate_for_currency(self, currency: Currency, quote: Currency) -> float:
        return self(currency, quote)


class MarginCalculator(ABC):

    @abstractmethod
    def compute_margin(self,
                       cash_positions: CashPositions,
                       domestic: Currency,
                       spot_fx_cache: SpotFxCache,
                       margin_rates: MarginRatesCache,
                       multiplier=2.0) -> float:
        raise NotImplementedError()

    def compute_required_cash_deposit_or_withdrawl(self,
                                                   cash_positions: CashPositions,
                                                   domestic: Currency,
                                                   spot_fx_cache: SpotFxCache,
                                                   margin_rates: MarginRatesCache,
                                                   target_health: float,
                                                   multiplier: object = 2.0) -> float:
        """
        Compute the amount of cash that needs to be deposited or withdrawn to reach a target health.
        :param cash_positions: The cash position
        :param domestic: the domestic currency
        :param spot_fx_cache: the spot fx cache
        :param margin_rates: the current margin rates
        :param target_health: the required target heath
        :param multiplier: the margin multiplier
        :return: a positive number for a required deposit, a negative number for a required withdrawl to reach the target health.
        """
        cash_by_currency = cash_positions.cash_by_currency
        total_cash = 0
        for currency, amount in cash_by_currency.items():
            total_cash += spot_fx_cache.convert_value(value=amount, from_currency=currency, to_currency=domestic)

        margin = self.compute_margin(cash_positions=cash_positions,
                                     domestic=domestic,
                                     spot_fx_cache=spot_fx_cache,
                                     margin_rates=margin_rates,
                                     multiplier=multiplier)
        if margin != 0:
            if (total_cash - margin) / margin > target_health:
                sign = -1
            else:
                sign = 1
        else:
            sign = 1

        def f(c):
            new_cash_positions = CashPositions(cash_by_currency=cash_by_currency.copy())
            new_cash_positions.add_cash(currency=domestic, amount=c[0])
            margin = self.compute_margin(cash_positions=cash_positions,
                                         domestic=domestic,
                                         spot_fx_cache=spot_fx_cache,
                                         margin_rates=margin_rates,
                                         multiplier=multiplier)
            return (total_cash + (c * sign) - margin) / margin - (target_health)

        solution = scipy.optimize.fsolve(f, [2 * margin])
        return solution[0] * sign

    def compute_margin_from_vfx(self,
                                virtual_fx: Iterable[VirtualFxPosition],
                                domestic: Currency,
                                spot_fx_cache: SpotFxCache,
                                margin_rates: MarginRatesCache,
                                additional_cash: Dict[Currency, float] = None,
                                multiplier=2.0) -> float:
        cash_positions = CashPositions()
        # Add cash from virtual Fx positions.
        for v_fx in virtual_fx:
            cash_positions.add_cash_from_virtual_fx(v_fx)

        # Potentially add additional cash.
        if additional_cash:
            for currency, amount in additional_cash.items():
                cash_positions.add_cash(currency=currency, amount=amount)
        return self.compute_margin(cash_positions=cash_positions,
                                   domestic=domestic,
                                   spot_fx_cache=spot_fx_cache,
                                   margin_rates=margin_rates,
                                   multiplier=multiplier)
