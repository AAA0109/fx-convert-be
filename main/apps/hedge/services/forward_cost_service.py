import abc
import logging
from typing import Dict, Optional

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Company
from main.apps.corpay.models import TransactionCost
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService

logger = logging.getLogger(__name__)


class Cost:
    def __init__(
        self,
        currency: Currency,
        spot: float,
        market_points: float,
        broker_cost: float,
        notional: float,
    ):
        self.spot = spot
        self.currency = currency
        self.market_points = market_points
        self.broker_cost = broker_cost
        self.notional = notional

    @property
    def forward_price(self) -> float:
        return self.spot + self.market_points


class FxForwardCostCalculator(abc.ABC):
    @abc.abstractmethod
    def add_forward(self, ref_date: Date, forward: DraftFxForwardPosition):
        raise NotImplementedError

    @abc.abstractmethod
    def costs(self) -> Dict[Currency, Cost]:
        raise NotImplementedError


class FxQuoteService(abc.ABC):

    @abc.abstractmethod
    def get_forward_points(
        self, company: Company, fxpair: FxPair, tenor: Date
    ) -> (float, float):
        """

        :param company: The company for which we are computing the forward points
        :param fxpair: The fxpair for which we are computing the forward points
        :param tenor:  The forward tenor
        :return: (Spot, Forward Points)
        """
        raise NotImplementedError


class FxQuoteServiceImpl(FxQuoteService):
    def __init__(self, universe_provider: UniverseProviderService):
        self._universe_provider = universe_provider

    def get_forward_points(
        self, company: Company, fxpair: FxPair, tenor: Date
    ) -> (float, float):
        universe = self._universe_provider.make_cntr_currency_universe(
            domestic=company.currency, ref_date=Date.today(), bypass_errors=True
        )

        spot_rate = universe.get_fx(fxpair)
        asset = universe.get_fx_asset(pair=fxpair)

        if not asset:
            logger.warning(f"Cannot find asset for {fxpair}, assuming flat forward.")
            fwd_value = spot_rate
        else:
            fwd_value = asset.fwd_curve.at_D(date=Date.from_datetime(tenor))
        if fwd_value is None or spot_rate is None:
            return 0, 0
        return spot_rate, fwd_value - spot_rate



class FxForwardCostCalculatorImpl(FxForwardCostCalculator):
    def __init__(self, fx_quote_servie: FxQuoteService,
                 spot_fx_cache: SpotFxCache):
        self._costs = {}
        self._fx_quote_service = fx_quote_servie
        self._spot_fx_cache = spot_fx_cache

    def add_forward(self, ref_date: Date, forward: DraftFxForwardPosition, risk_reduction: Optional[float] = None):
        # Added this so we can calculate cost that is not tied to forward.risk_reduction
        if risk_reduction is not None:
            _notional = forward.notionals_in_company_currency(
                ref_date=ref_date,
                spot_fx_cache=self._spot_fx_cache,
                risk_reduction=risk_reduction
            )
        else:
            _notional = forward.notionals_in_company_currency(
                ref_date=ref_date,
                spot_fx_cache=self._spot_fx_cache
            )
        for tenor, notional in zip(
            forward.tenors(ref_date=ref_date), _notional
        ):
            (spot, fwd_points) = self._fx_quote_service.get_forward_points(
                company=forward.company, fxpair=forward.fxpair, tenor=tenor
            )
            # The following bit of code is a workaround in order to get the cost associated
            # with the correct currency.
            if forward.fxpair.base == forward.company.currency:
                cny = forward.fxpair.quote_currency
            else:
                cny = forward.fxpair.base_currency
            cost = TransactionCost.get_cost(company=forward.company, notional_in_usd=notional, currency=cny)
            if not cost:
                if forward.company.currency not in self._costs:
                    self._costs[forward.company.currency] = Cost(
                        forward.fxpair.base_currency,
                        spot,
                        fwd_points,
                        0,
                        notional
                    )
                logger.warning("No cost found for forward %s", forward)
                continue
            if cost and forward.company.currency not in self._costs.keys():
                self._costs[forward.company.currency] = Cost(
                    forward.fxpair.base_currency,
                    spot,
                    fwd_points,
                    cost.broker_cost,
                    notional,
                )
            else:
                # we compute the average of the previous cost and the new cost wighted by the notionals
                prev_cost = self._costs[forward.company.currency]
                total_notional = prev_cost.notional + notional
                prev_weight = prev_cost.notional / total_notional
                new_weight = notional / total_notional
                self._costs[forward.company.currency] = Cost(
                    currency=forward.fxpair.base_currency,
                    spot=prev_cost.spot,
                    market_points=prev_cost.market_points * prev_weight + fwd_points * new_weight,
                    broker_cost=prev_cost.broker_cost * prev_weight + cost.broker_cost * new_weight,
                    notional=total_notional,
                )

    def costs(self) -> Dict[Currency, Cost]:
        return self._costs

    def cost(self, currency: Currency) -> Optional[Cost]:
        """If we have a quote for the currency, return the cost, otherwise return None"""
        return self._costs.get(currency, None)

    def broker_cost_in(self, currency: Currency, spot_fx_cache: SpotFxCache) -> float:
        broker_cost = 0

        for cny, cost in self.costs().items():
            if cny == currency:
                broker_cost += cost.broker_cost * abs(cost.notional)
            else:
                broker_cost += cost.broker_cost * spot_fx_cache.convert_value(cost.notional, cny, currency)
        return abs(broker_cost)


    def notional_in(self, currency: Currency, spot_fx_cache: SpotFxCache) -> float:
        notional = 0

        for cny, cost in self.costs().items():
            if cny == currency:
                notional += cost.notional
            notional += spot_fx_cache.convert_value(cost.notional, cny, currency)
        return notional
