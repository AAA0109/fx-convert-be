from functools import lru_cache
from typing import List, Tuple, Dict

import numpy as np
import scipy.stats
from scipy.stats import norm

from main.apps.account.models.parachute_data import ParachuteData
from hdlib.Hedge.Fx.CashPnLAccount import CashPnLAccountHistoryProvider
from hdlib.Hedge.Fx.HedgeCostProvider import HedgeCostProvider
from hdlib.Universe import Universe
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache, FxMarketConverter
from hdlib.Hedge.Fx.HedgeAccount import HedgeAccountSettings
from hdlib.Hedge.Fx.HedgeAccount import CashExposures

from main.apps.core.utils.cache import redis_func_cache
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.calculators.company_hedge import CompanyHedgeCalculator, AccountPositionsProviderStored, \
    CompanyHedgeCallback

from main.apps.hedge.models.fxforwardposition import FxForwardPosition

from main.apps.hedge.models import CompanyHedgeAction, HedgeSettings, FxPosition

from main.apps.hedge.services.account_history import CashPnLAccountHistoryProvider_DB
from main.apps.hedge.services.cost import CostProviderService
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.margin.services.margin_service import MarginProviderService, DefaultMarginProviderService
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.marketdata.services.universe_provider import UniverseProviderService

from main.apps.account.services.cashflow_provider import CashFlowProviderService, CashFlowProviderInterface
from main.apps.account.models import Company, Account, CashFlow

# Logging.
import logging

from main.apps.util import ActionStatus

logger = logging.getLogger(__name__)


@redis_func_cache(key=None, timeout=60 * 60 * 20, delete=False)
@lru_cache(typed=True, maxsize=2)
def caching_make_cntr_currency_universe(
    domestic: Currency,
    ref_date: Date,
    bypass_errors: bool = True,
):
    return UniverseProviderService().make_cntr_currency_universe(domestic=domestic,
                                                                 ref_date=ref_date,
                                                                 bypass_errors=bypass_errors)


class CompanyHedgerFactory(object):
    def __init__(self,
                 fx_market_convention_service: FxMarketConventionService = FxMarketConventionService(),
                 cashflow_provider: CashFlowProviderInterface = CashFlowProviderService(),
                 margin_provider: MarginProviderService = DefaultMarginProviderService(),
                 universe_provider_service: UniverseProviderService = UniverseProviderService(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 cost_provider: CostProviderService = CostProviderService()
                 ):
        self._fx_market_convention_service = fx_market_convention_service
        self._cashflow_provider = cashflow_provider
        self._margin_provider = margin_provider
        self._universe_provider_service = universe_provider_service
        self._hedge_position_service = hedge_position_service
        self._cost_provider = cost_provider

    def create(self,
               company: Company,
               account_data: Dict[
                   HedgeAccountSettings, Tuple[CashExposures, CashExposures, CashPnLAccountHistoryProvider]],
               date: Date,
               spot_cache: SpotFxCache,
               ) -> 'CompanyHedgeCalculator':
        # NOTE(Nate): I made this function to avoid the warning that settings does not have the attribute
        # to_HedgeAccountSettingsHDL.
        def to_settings(settings):
            if isinstance(settings, HedgeSettings):
                return settings.to_HedgeAccountSettingsHDL()
            return settings

        account_data_inner = {
            to_settings(settings): (exposure,
                                    forward_exposure,
                                    pnl_provider) for
            settings, (exposure, forward_exposure, pnl_provider) in account_data.items()}
        return CompanyHedgeCalculator(
            company=company,
            account_data=account_data_inner,
            universe=caching_make_cntr_currency_universe(company.currency, date, bypass_errors=True),
            cost_provider=self._cost_provider.get_cost_provider(date, spot_cache, domestic=company.currency),
            market_converter=self._fx_market_convention_service.make_fx_market_converter(is_hedge_supported_only=True))


def hedge_company(hedge_time: Date,
                  company_hedge_action: CompanyHedgeAction,
                  hedge_account_types: List[Account.AccountType],
                  cost_provider: HedgeCostProvider,
                  universe: Universe,
                  market_converter: FxMarketConverter,
                  callback: CompanyHedgeCallback
                  ):
    """
    The function to do a complete hedge of a company, given the basic data and objects that configure the hedge.
    """

    # Get the company from the hedge action.
    company = company_hedge_action.company

    # =============================================================================================================
    # Get all accounts and their current positions, cash exposures, and history providers for each of them.
    # =============================================================================================================

    # Get the account settings of all active accounts.
    # TODO: Make get_all_accounts_to_hedge time dependent, so we can get historical account settings.
    active_settings = [settings for settings in
                       HedgeSettings.get_all_accounts_to_hedge(company=company, account_types=hedge_account_types)
                       if settings.account.is_active
                       and settings.account.strategy in (Account.AccountStrategy.SPOT_HEDGING,
                                                         Account.AccountStrategy.HARD_LIMITS)]
    # Get a list of all active accounts.
    active_accounts = list(map(lambda settings: settings.account, active_settings))

    if len(active_accounts) == 0:
        return ActionStatus.log_and_no_change(f"No active spot-hedging accounts for company {company}.")

    logger.debug(f"Company {company} has {len(active_accounts)} active accounts. "
                f"Getting positions for active accounts.")
    positions, events = FxPosition.get_positions_for_accounts(time=hedge_time,
                                                              accounts=active_accounts)
    if 1 < len(events):
        logger.warning(f"Multiple events were the 'most recent' event for this company's accounts, this should not"
                       f"be possible")
    else:
        for event in events:  # There is only one.
            logger.debug(f"The events associated with the most recent positions is event {event.id}.")

    # Convert to dictionary of positions per fx pair per account.
    logger.debug(f"Converting positions into format for CompanyHedgeCalculator.")
    account_positions = {}
    for position in positions:
        account_positions.setdefault(position.account, {})[position.fxpair] = position.amount

    # Get account data: a map from account settings to tuples of (CashExposures, CashPnLAccountHistoryProvider).
    # TODO: More efficient to get all cashflows for a company in one query, then divide them up.
    account_data = {}
    count_accounts_with_net_exposures = 0
    for settings in active_settings:
        settings = settings.to_HedgeAccountSettingsHDL()
        # Get cash exposures, not including forwards. These are the raw cash exposures.
        raw_cash_exposures = CashFlowProviderService().get_cash_exposures(date=hedge_time, settings=settings,
                                                                          include_forwards=False)
        # Get cash exposures, including forwards.
        cash_exposures = CashFlowProviderService().get_cash_exposures(date=hedge_time, settings=settings,
                                                                      include_forwards=True)
        cash_pnl_account_history_provider = CashPnLAccountHistoryProvider_DB(settings=settings)
        account_data[settings] = (cash_exposures, raw_cash_exposures, cash_pnl_account_history_provider)

        if 0 < len(cash_exposures.net_exposures()):
            count_accounts_with_net_exposures += 1

    logger.debug(f"Retrieved cash exposures for {len(active_accounts)} accounts. "
                f"There are {count_accounts_with_net_exposures} with net exposures.")
    for settings, (cash_exposures, _, _) in account_data.items():
        if 0 < len(cash_exposures.net_exposures()):
            logger.debug(f"Cash exposures for account '{settings.account_name}': ")
            for fxpair, exposure in cash_exposures.net_exposures().items():
                logger.debug(f"  * {fxpair}: {exposure}")

    # Create an account position provider
    positions_provider = AccountPositionsProviderStored(fxspot_positions=account_positions)

    # =============================================================================================================
    #  Create and run a Hedge calculator.
    # =============================================================================================================

    # Create a company hedge calculator to run the hedging.
    hedger = CompanyHedgeCalculator(company=company,
                                    account_data=account_data,
                                    universe=universe,
                                    cost_provider=cost_provider,
                                    market_converter=market_converter,
                                    callback=callback)
    # Run the hedger.
    try:
        logger.debug(f"Hedging company {company} using CompanyHedgeCalculator.")
        hedger.hedge_company(positions_provider=positions_provider)
        logger.debug(f"Done hedging company {company}. No exceptions raised.")
    except Exception as ex:
        return ActionStatus.log_and_error(f"Error hedging company: {ex}")

    return ActionStatus.log_and_success(f"Successfully hedged company {company} at {hedge_time}.")
