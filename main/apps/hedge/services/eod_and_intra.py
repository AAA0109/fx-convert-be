import datetime
import logging
from typing import Tuple, Dict, Optional

from hdlib.Core.Currency import USD
from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.Hedge.Fx.HedgeCostProvider import HedgeCostProvider
from hdlib.Universe.Universe import Universe

from main.apps.account.models import Company, Currency
from main.apps.broker.models import Broker
from main.apps.account.models import Company, Currency, CashFlow, Account, iter_active_cashflows, \
    ParachuteCashFlow
from main.apps.currency.models import FxPair
from main.apps.events.services.instrument_service import InstrumentService
from main.apps.hedge.calculators.RatesCache import BrokerRatesCaches
from main.apps.hedge.models import CompanyHedgeAction, CompanyTypes
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.account_manager import AccountManagerService, AccountManagerInterface, \
    BacktestAccountManagerService
from main.apps.hedge.services.broker import BacktestingBrokerService, BrokerService
from main.apps.hedge.services.broker_reconcile import BrokerReconcileService, StandardReconciliationCallback, \
    BacktestBrokerReconcileService
from main.apps.hedge.services.cost import CostProviderService
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.services.hedger import hedge_company
from main.apps.hedge.services.oms import OMSHedgeService, BacktestOMSHedgeService, OMSHedgeServiceInterface
from main.apps.hedge.services.parachute_hedger import hedge_parachute
from main.apps.hedge.support.standard_company_hedge_callback import StandardCompanyHedgeCallback
from main.apps.history.services.snapshot import SnapshotCreatorService
from main.apps.margin.services.margin_service import DefaultMarginProviderService, \
    BacktestMarginProviderService, MarginProviderServiceInterface
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.oems.services.order_service import OrderService, OrderServiceInterface, BacktestOrderService
from main.apps.util import ActionStatus

logger = logging.getLogger(__name__)


class EodAndIntraService:
    """
    Service responsible for defining EOD and Intra day flows related to hedging / account management.
    """

    def __init__(self,
                 ref_date: Date,
                 fx_provider: FxSpotProvider = FxSpotProvider(),
                 margin_provider: MarginProviderServiceInterface = DefaultMarginProviderService(),
                 oms_hedge_service: OMSHedgeServiceInterface = OMSHedgeService(),
                 account_manager: AccountManagerInterface = AccountManagerService(),
                 broker_reconcile_service: BrokerReconcileService = BrokerReconcileService(),
                 universe_provider_service: UniverseProviderService = UniverseProviderService(),
                 cost_provider_service: CostProviderService = CostProviderService(),
                 market_convention_service: FxMarketConventionService = FxMarketConventionService(),
                 order_service: OrderServiceInterface = OrderService(),
                 broker_service: BrokerService = BrokerService()):

        self._ref_date = Date.to_date(ref_date)  # This must be enforced as an hdlib date

        self._margin_provider = margin_provider
        self._oms_hedge_service = oms_hedge_service
        self._account_manager = account_manager
        self._broker_reconcile_service = broker_reconcile_service
        self._cost_provider_service = cost_provider_service
        self._order_service = order_service
        self._market_convention_service = market_convention_service

        try:
            self._spot_cache = fx_provider.get_spot_cache(time=self._ref_date)
        except Exception as ex:
            self._spot_cache = None
            logger.error(f"Could not create spot fx cache on {self._ref_date}:{ex}")
            # TODO: pub/sub - this is a major error.

        self._universes: Dict[Currency, Universe] = {}  # Dictionary from domestic (counter currency) to universe
        self._load_universes(universe_provider_service=universe_provider_service)

        self._rates_caches: BrokerRatesCaches = self._load_rates_caches()

        self._snapshot_service = SnapshotCreatorService(universes=self._universes,
                                                        rates_caches=self._rates_caches,
                                                        broker_service=broker_service)

    def get_universe(self):
        # TODO: Support for non-USD domestics.
        return self._universes[USD]

    def start_eod_flow_for_company(self, time: Date, company: CompanyTypes) -> ActionStatus:
        """
        This starts the EOD flow for a company, which includes:
            1) tidying up loose ends since the last run,
            2) reconciling company accounts
            3) EOD account management
            4) Margin Checkup
            5) Hedging
        :param time: the time at which the EOD flow starts.
        :param company: identifier of a company
        :return: ActionStatus, indication of what happened
        """
        company_ = Company.get_company(company)
        if not company_:
            return ActionStatus.log_and_error(f"Can't start EOD for company:{company_}, not found")
        # TODO: use pub/sub in case of errors to publish the error so that some other process can handle it

        logger.debug(f"Starting EOD flow for company: {company_}")

        # Pre-step: generate cashflows for parachute accounts.
        # NOTE(Nate): When we separate Cashflows from generators, this will be a separate step, and not specific to a company.
        self.generate_cashflows(company=company_)

        # ==========================
        # 1) Run reconciliations (before we do any hedging, make sure we agree with broker on state of reality)
        # ==========================

        # We do the reconciliation first so we are ready in case we need to e.g. close an account. We can only do that
        # after the account has been reconciled, so doesn't think it has any outstanding orders or anything.
        logger.debug(f"Starting pre-hedge company reconciliation for {company_}")
        callback = StandardReconciliationCallback(self._broker_reconcile_service)
        self._broker_reconcile_service.reconcile_company(time=time, company=company_, spot_cache=self._spot_cache,
                                                         callback=callback)
        # Do the bookkeeping of closing any forwards that delivered since the last EOD.
        last_action = CompanyHedgeAction.get_latest_company_hedge_action(time=time, company=company_)
        last_action_time = Date.from_datetime(last_action.time) if last_action else None
        self._close_delivered_forwards(time=time, last_hedge_action_time=last_action_time,
                                       company=company_)
        self._register_rolled_off_cashflows(time=time,
                                            last_hedge_action_time=last_action_time,
                                            company=company_)

        # ==========================
        # 2) Run EOD Account Management.
        # ==========================

        # Create a company hedge action.
        logger.debug(f"Adding company hedge action for company {company_}")
        status, company_hedge_action = CompanyHedgeAction.add_company_hedge_action(company=company_,
                                                                                   time=self._ref_date)
        if not status.is_success():
            return ActionStatus.log_and_error(f"Error creating a CompanyHedgeAction: {status}")
        logger.debug(f"Created company hedge action {company_hedge_action.id} for company {company_}.")

        # Handle e.g. account activations, deactivations, changes in company status, etc.
        status = self._account_manager.run_eod(company=company_)
        if status.is_error():
            # TODO: publish error.
            return status

        if company_.status != Company.CompanyStatus.ACTIVE:
            return ActionStatus.success("Company is inactive, nothing more to do")

        # ==========================
        # 4) Hedging.
        # ==========================

        status, _ = self.hedge_company(company=company_, company_hedge_action=company_hedge_action,
                                       error_account_types={})
        if status.is_error():
            # TODO: publish that EOD hedge failed
            logger.error(f"Hedging company {company_} failed: {status}")
            return status

        # At this point, we will need to wait until the OMS actually goes to IB and executes orders.
        return status.log_and_success(f"Done starting EOD flow for {company_}")

    def end_eod_flow_for_company(self, time: Date, company: CompanyTypes) -> ActionStatus:
        """
        This Ends the EOD flow for a company, which includes:
            1) Post-Hedge Reconciliation
            2) Parachute Hedging
            2) Post-Hedge Margin Checkup
            3) Account and Company Snapshots
        :param time: time at which the end starts.
        :param company: identifier of a company
        :return: ActionStatus, indication of what happened
        """
        # Hopefully, at this point, the OMS/EMS have actually done their thing and done all the trading that we wanted
        # to happen.
        company_ = Company.get_company(company)
        if not company_:
            return ActionStatus.log_and_error(f"Can't end EOD for company:{company_}, not found")

        # ==========================
        # 6) Fill in OMSOrderRequests
        # ==========================

        company_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company_, time=time)
        try:
            logger.debug(f"Completing OMS order requests from hedge action id = {company_hedge_action.id}")
            self._order_service.complete_oms_order_requests(company_hedge_action)
        except Exception as ex:
            logger.error(f"Error completing OMS order requests: {ex}")

        # ==========================
        # 7) Do post-hedge reconciliation.
        # ==========================

        logger.debug(f"Starting post-hedge company reconciliation for {company_}.")
        callback = StandardReconciliationCallback(self._broker_reconcile_service)
        self._broker_reconcile_service.reconcile_company(time=time, company=company_, spot_cache=self._spot_cache,
                                                         callback=callback)
        logger.debug(f"Done with post-hedge company reconciliation for {company_}.")

        # ==========================
        # 7)  Hedge parachute type accounts.
        # ==========================

        logger.debug(f"Running parachute (if applicable).")
        universe = self._universes.get(company_.currency)
        hedge_parachute(hedge_time=time, company_hedge_action=company_hedge_action, universe=universe)
        logger.debug(f"Done running parachute.")

        # ==========================
        # 8) Take company and accounts snapshot.
        # ==========================
        try:
            logger.debug(f"Creating EOD snapshots for company {company_}.")
            self._snapshot_service.set_time(time)
            self._snapshot_service.create_full_snapshot_for_company(company=company_)
            logger.debug(f"Done creating EOD snapshots for company {company_}.")
        except Exception as ex:
            logger.error(f"Error creating EOD snapshots for company {company_}: {ex}")
            # TODO: handle this? It is bad if we can't create a snapshot.
            raise ex

        # ==========================
        # 9) Post-hedge margin check up.
        # ==========================
        # Make sure that running the hedge does not result in needing more margin.
        # Make sure we have an up-to-date view of whether the company has enough margin.
        logger.debug(f"Running post hedge margin check for company {company_}.")
        try:
            margin_detail = self._margin_provider.get_margin_detail(company=company_, date=self._ref_date)
            if margin_detail and margin_detail.get_margin_health().is_unhealthy:
                return ActionStatus.error("Account is now in need of margin.")
        except Exception as e:
            logging.warning(f"Unable to run post hedge margin check for company {company_}.")

        return ActionStatus.success(f"EOD flow complete for company {company_}")

    def generate_cashflows(self, company: Company):
        """
        Generate cashflows that should be generated for all parachute accounts from the cashflow generators.

        NOTE(Nate): This should eventually be run as a separate step EOD before any hedging, not as a per-company step.
        """

        logger.debug(f"Generating cashflows for company {company}.")

        # TODO: Don't have a hard-coded end horizon. Eventually, this can be a property of the generator.
        end_horizon = self._ref_date + 365
        logger.debug(f"Generating cashflows for company {company} with end horizon {end_horizon}.")

        account_strategy_types = (Account.AccountStrategy.PARACHUTE, Account.AccountStrategy.HARD_LIMITS)
        parachute_accounts = Account.get_account_objs(company=company,
                                                      strategy_types=account_strategy_types,
                                                      exclude_hidden=True)
        logger.debug(f"Found {len(parachute_accounts)} parachute accounts for company {company}.")

        total_cashflows_created = 0
        for account in parachute_accounts:
            domestic = account.domestic_currency
            account_cashflows_created = 0

            # Get all Cashflow generators for this account
            generators = CashFlow.get_cashflow_object(start_date=self._ref_date, account=account)
            for generator in generators:
                last_generated_point = generator.last_generated_point
                if last_generated_point and end_horizon <= last_generated_point:
                    logger.debug(f"Last generated point for cashflow generator {generator.id} is "
                                 f"{last_generated_point}, which is before the end horizon {end_horizon}. Skipping.")
                    continue

                next_point = Date.to_date(last_generated_point) + datetime.timedelta(
                    days=1) if last_generated_point else self._ref_date
                cfs = iter_active_cashflows(cfs=(generator,), ref_date=next_point, max_date_in_future=end_horizon)

                # TODO: Use transaction.

                # Add corresponding Parachute cashflows, and then set the last generated point in the generator.

                for cashflow in cfs:
                    initial_npv = self._universes[domestic].value_cashflow(cashflow, quote_currency=domestic)
                    initial_spot = self._universes[domestic].convert_value(value=1, from_currency=cashflow.currency, to_currency=domestic)
                    logger.debug(f"Adding parachute cashflow for cashflow generator {generator.id}, pay date "
                                 f"{cashflow.pay_date}, currency {cashflow.currency}, amount {cashflow.amount}, "
                                 f"initial npv {initial_npv}, initial spot {initial_spot}.")

                    ParachuteCashFlow.create_cashflow(account=account,
                                                      pay_date=cashflow.pay_date,
                                                      currency=cashflow.currency,
                                                      amount=cashflow.amount,
                                                      generation_time=self._ref_date,
                                                      initial_npv=initial_npv,
                                                      initial_spot=initial_spot)
                    account_cashflows_created += 1
                generator.last_generated_point = end_horizon
                generator.save()
            total_cashflows_created += account_cashflows_created
            logger.debug(f"Created {account_cashflows_created} cashflows for account {account}.")

        logger.debug(f"Done generating cashflows for company {company}. "
                    f"Created a total of {total_cashflows_created} cashflows.")

    def hedge_company(self,
                      company: Company,
                      company_hedge_action: CompanyHedgeAction,
                      error_account_types=None
                      ) -> Tuple[ActionStatus, CompanyHedgeAction]:
        """
        Run the hedging for a company. This involves running the hedging on both live and demo accounts, and then
        reconciling demo accounts (since we do not have to wait for orders).

        The actual hedging logic is encoded in the CompanyHedgeCalculator, the rest of the function just orchestrates
        the call to the calculator.
        """

        hedge_time = self._ref_date
        spot_cache = self._spot_cache

        logger.debug(f"Hedging company {company}.")
        if error_account_types is None:
            error_account_types = set({})

        # TODO: These can be stored in the EOD service.
        # TODO: broker is hard coded
        cost_provider = self._cost_provider_service.get_cost_provider(date=hedge_time, fx_cache=spot_cache,
                                                                      domestic=company.currency,
                                                                      broker="IBKR")

        universe = self._universes.get(company.currency)

        # Run standard spot hedging.
        status = self._standard_hedge(hedge_time=hedge_time,
                                      company_hedge_action=company_hedge_action,
                                      universe=universe,
                                      cost_provider=cost_provider,
                                      error_account_types=error_account_types)

        # Return status and action.
        return status, company_hedge_action

    # ================
    # Private
    # ================

    def _standard_hedge(self, hedge_time: Date,
                        company_hedge_action: CompanyHedgeAction,
                        universe: Universe,
                        cost_provider: HedgeCostProvider,
                        error_account_types=None) -> ActionStatus:
        logger.debug(f"Running hedges for standard accounts")

        # =============================================================================================================
        # Get all accounts and their current positions, cash exposures, and history providers for each of them.
        # =============================================================================================================
        company = company_hedge_action.company

        # Get LIVE and DEMO accounts unless they failed.
        hedge_account_types = [acc_type for acc_type in OMSHedgeService.hedgeable_account_types
                               if acc_type not in error_account_types]
        logger.debug(f"Hedge-able account types = {hedge_account_types} "
                    f"(account error types was {error_account_types}).")

        # Create a callback object that creates account hedge requests.
        callback = StandardCompanyHedgeCallback(company_hedge_action=company_hedge_action,
                                                universe=self._universes.get(company.currency),
                                                oms_hedge_service=self._oms_hedge_service,
                                                margin_provider_service=self._margin_provider)

        status = hedge_company(hedge_time=hedge_time,
                               company_hedge_action=company_hedge_action,
                               cost_provider=cost_provider,
                               hedge_account_types=hedge_account_types,
                               market_converter=self._market_convention_service.make_fx_market_converter(),
                               universe=universe,
                               callback=callback)
        return status

    def _close_delivered_forwards(self, time: Date, last_hedge_action_time: Optional[Date], company: Company):
        logger.debug(f"Closing any Fx forwards that delivered since last EOD.")

        count, pnl = InstrumentService.close_delivered_forwards(company=company, start_time=last_hedge_action_time,
                                                                end_time=time,
                                                                spot_fx_cache=self._spot_cache)

        if 0 < count:
            logger.debug(f"There were {count} forwards delivered between {last_hedge_action_time} and {time} (now), "
                        f"total realized PnL was {pnl}.")
        else:
            logger.debug(f"No forwards delivered between {last_hedge_action_time} and {time} (now).")

    def _register_rolled_off_cashflows(self, time: Date, last_hedge_action_time: Optional[Date], company: Company):
        # Handle "parachute" cashflows.
        InstrumentService.register_cashflow_rolloffs_eod(time=time)

        if not last_hedge_action_time:
            return

        rolled_off = InstrumentService.register_cashflow_rolloffs(company=company, start_time=last_hedge_action_time,
                                                                  end_time=time, spot_fx_cache=self._spot_cache)
        logger.debug(f"Registered {rolled_off} cashflows as having rolled off.")

    def _load_rates_caches(self) -> BrokerRatesCaches:
        # TODO: create broker provider service, or put this into an account related service, e.g. AccountManagerService
        try:
            brokers = Broker.objects.all()
            return self._cost_provider_service.create_all_rates_caches(time=self._ref_date,
                                                                       brokers=brokers)
        except Exception as e:
            logger.error(f"Error loading broker rates caches: {e}")
            return BrokerRatesCaches()

    def _load_universes(self, universe_provider_service: UniverseProviderService):
        # Loads a universe for every supported domestic currency (currently just USD)
        try:
            usd = Currency.get_currency("USD")  # In the future, we load for a set of specified domestics
            domestics = set()
            domestics.add(usd)

            self._universes = universe_provider_service.make_cntr_currency_universes_by_domestic(
                domestics=domestics, ref_date=self._ref_date, bypass_errors=True, spot_fx_cache=self._spot_cache,
                all_or_none=False)

        except Exception as e:
            # TODO: pub/sub - this is a major error.
            logger.error(f"Error creating universes for EOD service: {e}")


class BacktestEodAndIntraService(EodAndIntraService):

    def __init__(self, ref_date: Date):
        fx_provider = FxSpotProvider()
        order_service = BacktestOrderService()
        oms_hedge_service = BacktestOMSHedgeService(order_service=order_service)
        hedge_position_service = HedgePositionService()
        hedge_request_service = AccountHedgeRequestService()
        account_manager = BacktestAccountManagerService(oms_hedge_service=oms_hedge_service,
                                                        hedge_position_service=hedge_position_service,
                                                        hedge_request_service=hedge_request_service)
        market_convention_service = FxMarketConventionService()
        broker_service = BacktestingBrokerService(order_service)
        broker_reconcile_service = BacktestBrokerReconcileService(broker_service=broker_service,
                                                                  oms_hedge_service=oms_hedge_service)
        universe_provider_service: UniverseProviderService = UniverseProviderService()
        cost_provider_service: CostProviderService = CostProviderService()

        margin_provider_service = BacktestMarginProviderService()
        super().__init__(ref_date=ref_date,
                         fx_provider=fx_provider,
                         oms_hedge_service=oms_hedge_service,
                         account_manager=account_manager,
                         broker_reconcile_service=broker_reconcile_service,
                         universe_provider_service=universe_provider_service,
                         cost_provider_service=cost_provider_service,
                         market_convention_service=market_convention_service,
                         margin_provider=margin_provider_service,
                         order_service=order_service,
                         broker_service=broker_service)
