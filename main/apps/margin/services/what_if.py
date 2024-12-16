import logging
from typing import Optional, Iterable, List

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.HedgeAccount import CashExposures_Cached
from hdlib.Hedge.Fx.Util.FxPnLCalculator import FxPnLCalculator
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.Utils import PnLCalculator

from main.apps.account.models import Company, Account, CashFlow, iter_active_cashflows
from main.apps.hedge.calculators.company_hedge import AccountPositionsProviderStored
from main.apps.hedge.models import FxPosition
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.services.hedger import CompanyHedgerFactory
from main.apps.hedge.tests.test_company_hedge import CashPnLAccountHistoryProvider_Empty
from main.apps.margin.models.margin import MarginDetail
from main.apps.margin.services.broker_margin_service import BrokerMarginServiceInterface, DbBrokerMarginService
from main.apps.margin.services.calculators import MarginCalculator
from main.apps.margin.services.calculators.ibkr import IBMarginCalculator
from main.apps.margin.services.margin_service import MarginProviderService
from main.apps.margin.services.margin_service import MarginRatesCacheProvider, \
    DBMarginRatesCashProvider, DefaultMarginProviderService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


class WhatIfMarginService(object):

    def __init__(self,
                 margin_calculator: MarginCalculator,
                 broker_service: BrokerMarginServiceInterface,
                 margin_rates_cache_provider: MarginRatesCacheProvider,
                 fx_spot_provider: FxSpotProvider,
                 hedge_position_service: HedgePositionService,
                 pnl_calculator: PnLCalculator,
                 hedger_factory: CompanyHedgerFactory,
                 margin_provider_service: MarginProviderService):
        self._margin_calculator = margin_calculator
        self._broker_service = broker_service
        self._margin_rates_cache_provider = margin_rates_cache_provider
        self._fx_spot_provider = fx_spot_provider
        self._hedge_position_service = hedge_position_service
        self._pnl_calculator = pnl_calculator
        self._hedger_factory = hedger_factory
        self._margin_provider_service = margin_provider_service

    @property
    def fx_spot_provider(self) -> FxSpotProvider:
        return self._fx_spot_provider

    def get_position_changes_what_if_after_trades(self,
                                                  date: Date,
                                                  company: Company,
                                                  new_cashflows: Iterable[CashFlow],
                                                  account_type: Account.AccountType = Account.AccountType.LIVE,
                                                  spot_fx_cache: Optional[SpotFxCache] = None
                                                  ) -> PositionChange:
        logger.debug("Calculating position changes for company %s after trades on %s with %d cashflows",
                    company, date, len(list(new_cashflows)))

        cashflow_by_account = {}
        accounts = []
        for cf in new_cashflows:
            currency = cf.currency
            if currency.get_mnemonic() != company.currency.get_mnemonic():
                cashflow_by_account.setdefault(cf.account, []).append(cf)
                accounts.append(cf.account)

        exposures = {}
        for account, cfs in cashflow_by_account.items():
            if not account.type == account_type:
                logger.debug("Skipping account %s because it is not of type %s", account, account_type)
                continue
            if not account.is_active:
                logger.debug("Skipping account %s because it is not active", account)
                continue
            if not account.has_hedge_settings():
                logger.warning("Skipping account %s because it has no hedge settings", account)
                continue
            hedge_settings = account.hedge_settings

            flows_by_currency = {}
            for cashflow in iter_active_cashflows(cfs=cfs, ref_date=date):
                flows_by_currency.setdefault(cashflow.currency, []).append(cashflow)

            exposures[account] = CashExposures_Cached(date=date,
                                                      cashflows=flows_by_currency,
                                                      settings=hedge_settings.to_HedgeAccountSettingsHDL())

        logger.debug("Getting spot fx rates for company %s on %s", company, date)
        spot_fx_cache = spot_fx_cache if spot_fx_cache is not None \
            else self._fx_spot_provider.get_spot_cache(time=date, window=20)

        logger.debug("Creating a hedger for company %s on %s", company, date)
        positions, events = FxPosition.get_positions_for_accounts(time=date, accounts=accounts)
        positions: List[FxPosition] = list(positions)
        logger.debug("Recalculating the hedges for company %s on %s", company, date)
        account_data = {
            acct.hedge_settings: (exposure,
                                  exposure,
                                  CashPnLAccountHistoryProvider_Empty())
            for acct, exposure in exposures.items()}
        logger.debug(f"Converting positions into format for CompanyHedgeCalculator for %s positions", len(positions))
        account_positions = {}
        for position in positions:
            if position.account not in account_positions:
                account_positions[position.account] = {}
            account_positions[position.account][position.fxpair] = position.amount
        # Create an account position provider
        positions_provider = AccountPositionsProviderStored(fxspot_positions=account_positions)
        logger.debug(f"Creating hedger")
        hedger = self._hedger_factory.create(date=date, company=company, spot_cache=spot_fx_cache,
                                             account_data=account_data)
        logger.debug("Hedging")
        ((_, old_new_positions, _), _) = hedger.hedge_company(positions_provider=positions_provider)
        return old_new_positions

    def compute_margin_for_position(self,
                                    date: Date,
                                    company: Company,
                                    old_new_positions: PositionChange,
                                    account_type: Account.AccountType = Account.AccountType.LIVE,
                                    spot_fx_cache: Optional[SpotFxCache] = None
                                    ) -> MarginDetail:

        return self._margin_provider_service.compute_margin_for_position(old_new_positions=old_new_positions,
                                                                         company=company,
                                                                         date=date,
                                                                         account_type=account_type,
                                                                         spot_fx_cache=spot_fx_cache)

    def get_margin_details_what_if_after_trades(self,
                                                date: Date,
                                                company: Company,
                                                new_cashflows: Iterable[CashFlow],
                                                account_type: Account.AccountType = Account.AccountType.LIVE,
                                                spot_fx_cache: Optional[SpotFxCache] = None
                                                ) -> MarginDetail:
        logger.debug("Calculating margin details for company %s after trades on %s with %d cashflows",
                    company, date, len(list(new_cashflows)))
        logger.debug("Getting position change before and after trades")
        old_new_positions = self.get_position_changes_what_if_after_trades(date=date, company=company,
                                                                           new_cashflows=new_cashflows,
                                                                           account_type=account_type,
                                                                           spot_fx_cache=spot_fx_cache)
        logger.debug("Computing margin for position change")
        return self._margin_provider_service.compute_margin_for_position(old_new_positions=old_new_positions,
                                                                         company=company,
                                                                         date=date,
                                                                         spot_fx_cache=spot_fx_cache)

    def get_company_margin_health_including_pending(self,
                                                    date: Date,
                                                    company: Company,
                                                    account_type: Account.AccountType = Account.AccountType.LIVE,
                                                    spot_fx_cache: Optional[SpotFxCache] = None
                                                    ) -> MarginDetail:
        logger.debug("Calculating margin health for company %s on %s", company, date)
        logger.debug("*** Getting cashflows including pending")
        cashflows = list(CashFlow.get_company_active_cashflows(company=company, include_pending_margin=True))

        logger.debug("Getting position change before and after trades")
        old_new_positions = self.get_position_changes_what_if_after_trades(date=date, company=company,
                                                                           new_cashflows=cashflows,
                                                                           account_type=account_type,
                                                                           spot_fx_cache=spot_fx_cache)
        logger.debug("Computing margin for position change")
        return self._margin_provider_service.compute_margin_for_position(old_new_positions=old_new_positions,
                                                                         company=company,
                                                                         date=date,
                                                                         spot_fx_cache=spot_fx_cache)


class DefaultWhatIfMarginInterface(WhatIfMarginService):
    def __init__(self,
                 margin_calculator: MarginCalculator = IBMarginCalculator(),
                 broker_service: BrokerMarginServiceInterface = DbBrokerMarginService(),
                 margin_rates_cache_provider: MarginRatesCacheProvider = DBMarginRatesCashProvider(),
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 pnl_calculator: PnLCalculator = FxPnLCalculator(),
                 hedger_factory: CompanyHedgerFactory = CompanyHedgerFactory()):
        super().__init__(margin_calculator=margin_calculator,
                         broker_service=broker_service,
                         margin_rates_cache_provider=margin_rates_cache_provider,
                         fx_spot_provider=fx_spot_provider,
                         hedge_position_service=hedge_position_service,
                         pnl_calculator=pnl_calculator,
                         hedger_factory=hedger_factory,
                         margin_provider_service=DefaultMarginProviderService(
                             margin_calculator=margin_calculator,
                             broker_service=broker_service,
                             margin_rates_cache_provider=margin_rates_cache_provider,
                             fx_spot_provider=fx_spot_provider,
                             hedge_position_service=hedge_position_service,
                             pnl_calculator=pnl_calculator))
