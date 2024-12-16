import abc
import logging
from functools import lru_cache

from django.core.exceptions import ObjectDoesNotExist
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.core.utils.cache import redis_func_cache
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.marketdata.services.universe_provider import UniverseProviderService

logger = logging.getLogger(__name__)


class CreditUtilizationService(abc.ABC):
    class Utilization:
        def __init__(self, credit_utilization: float, credit_limit: float, forward_pnl: float):
            self.credit_utilization = credit_utilization
            self.credit_limit = credit_limit
            self.forward_pnl = forward_pnl

        def get_credit_utilization_pct(self) -> float:
            if self.credit_limit == 0:
                return 0
            return self.credit_utilization / self.credit_limit

        def available(self) -> float:
            return self.credit_limit - self.credit_utilization

        def margin_call_at(self, margin_call_pct: float = 0.05) -> float:
            return -1 * (self.credit_limit * margin_call_pct)

    def __init__(self):
        pass

    @abc.abstractmethod
    def get_credit_utilization(self, company: Company) -> Utilization:
        pass


class CorPayCreditUtilizationService(CreditUtilizationService):

    def __init__(self, universe_provider: UniverseProviderService = UniverseProviderService()):
        super().__init__()
        self._universe_provider = universe_provider

    @redis_func_cache(key=None, timeout=60 * 60 * 20, delete=False)
    @lru_cache(typed=True, maxsize=2)
    def get_credit_utilization(self, company: Company) -> CreditUtilizationService.Utilization:
        try:
            company.corpaysettings
        except ObjectDoesNotExist:
            return CreditUtilizationService.Utilization(credit_utilization=0.0, credit_limit=0.0, forward_pnl=0.0)

        fwds = FxForwardPosition.get_forwards_for_company(company=company, current_time=Date.now())
        utilization = 0.0
        pnl = 0.0
        limit = company.corpaysettings.credit_facility

        universe = self._universe_provider.make_cntr_currency_universe(domestic=company.currency,
                                                                       ref_date=Date.today(),
                                                                       bypass_errors=True
                                                                       )
        logger.debug(f"Computing P&L for {company}")
        for forward in fwds:
            asset = universe.get_fx_asset(pair=forward.get_fxpair())
            if not asset:
                logger.warning(f"Cannot find asset for {forward.get_fxpair()}, assuming flat forward.")
                fwd_value = universe.get_fx(forward.get_fxpair())
            else:
                fwd_value = asset.fwd_curve.at_D(date=Date.from_datetime(forward.get_delivery_time()))
            val = (fwd_value - forward.get_forward_price()) * forward.get_amount()
            base_currency = forward.get_fxpair().get_base_currency()
            quote_currency = forward.get_fxpair().get_quote_currency()
            if forward.cashflow.amount > 0:
                pnl += universe.convert_value(value=val, from_currency=quote_currency, to_currency=company.currency)
            else:
                pnl += universe.convert_value(value=val, from_currency=base_currency, to_currency=company.currency)
            utilization += abs(universe.convert_value(value=forward.amount,
                                                  from_currency=base_currency,
                                                  to_currency=company.currency))
            logger.debug(f" * {forward.get_fxpair()} - {forward.amount} {forward.delivery_time.date()}@{forward.get_forward_price()} current price {fwd_value} pnl {val}. Total IN USD {pnl}")
        return CreditUtilizationService.Utilization(credit_utilization=utilization, credit_limit=limit, forward_pnl=pnl)

