from abc import abstractmethod, ABCMeta
from typing import Dict, Optional, List, Tuple

import numpy as np
from hdlib.Core.AccountInterface import AccountInterface

from hdlib.Core.FxPairInterface import FxPairInterface

from hdlib.DateTime import Date
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from main.apps.account.models import Account, Company
from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import FxPair
from main.apps.hedge.calculators.reconciliation import ReconciliationCalculator
from main.apps.hedge.models import CompanyHedgeAction, FxPosition, AccountHedgeRequest, CompanyEvent, \
    AccountDesiredPositions
from main.apps.hedge.models.company_accrued_cash import CompanyAccruedCash
from main.apps.hedge.models.company_cash_holding import CompanyCashHolding
from main.apps.hedge.models.company_fxposition import CompanyFxPosition
from main.apps.hedge.models.demo_orders import DemoOrders
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.broker import BrokerService, BrokerServiceInterface, BacktestingBrokerService
from main.apps.hedge.services.oms import OMSHedgeService, OMSHedgeServiceInterface, BacktestOMSHedgeService
from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface
from main.apps.hedge.support.fxposition_interface import FxPositionInterface
from main.apps.history.models import ReconciliationRecord
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService

import logging

logger = logging.getLogger(__name__)


class ReconciliationCallback:
    """
    A class that handles the creation or fetching of objects during reconciliation. This is packaged as its own
    mini-service, or set of call back functions, to make it easier to have a "check reconciliation" flow that
    doesn't actually save anything to the database or create new positions or company events, but allows us to follow
    a reconciliation from the past without changing anything in the database.
    """

    @abstractmethod
    def update_hedge_result(self,
                            result: AccountHedgeResultInterface,
                            status: AccountHedgeRequest.OrderStatus = AccountHedgeRequest.OrderStatus.CLOSED):
        raise NotImplementedError

    @abstractmethod
    def create_company_positions(self, company: Company, time: Date, spot_cache: SpotFxCache) -> CompanyEvent:
        raise NotImplementedError

    @abstractmethod
    def create_reconciliation_records(self, company: Company, time: Date, reconciliation_data, is_live: bool):
        raise NotImplementedError

    @abstractmethod
    def create_fx_positions(self,
                            final_positions_by_fxpair: Dict[
                                FxPairInterface, Dict[AccountInterface, FxPositionInterface]],
                            company_event: CompanyEvent):
        raise NotImplementedError


class StandardReconciliationCallback(ReconciliationCallback):
    """
    The standard reconciliation callback, for use during normal operations. Actually creates company events and company
    FX positions.
    """

    def __init__(self, broker_reconciliation_service: 'BrokerReconcileService'):
        self._broker_reconciliation_service = broker_reconciliation_service

    def update_hedge_result(self,
                            result: AccountHedgeResultInterface,
                            status: AccountHedgeRequest.OrderStatus = AccountHedgeRequest.OrderStatus.CLOSED):
        result.status = status
        if isinstance(result, AccountHedgeRequest):
            result.save()

    def create_company_positions(self, company: Company, time: Date, spot_cache: SpotFxCache) -> CompanyEvent:
        return self._broker_reconciliation_service.create_company_positions(time=time, company=company,
                                                                            spot_fx_cache=spot_cache)

    def create_fx_positions(self,
                            final_positions_by_fxpair: Dict[
                                FxPairInterface, Dict[AccountInterface, FxPositionInterface]],
                            company_event: CompanyEvent):
        self._broker_reconciliation_service.create_fx_positions(final_positions_by_fxpair, company_event=company_event)

    def create_reconciliation_records(self, company: Company, time: Date, reconciliation_data, is_live: bool):
        if 0 < len(reconciliation_data):
            logger.debug(f"Creating demo reconciliation data {len(reconciliation_data)} entries.")
            ReconciliationRecord.create_from_reconciliation_data(company=company, time=time, is_live=is_live,
                                                                 reconciliation_data=reconciliation_data)
        else:
            logger.debug(f"No demo reconciliation data with which to make entries.")


class BrokerReconcileServiceInterface(metaclass=ABCMeta):
    @abstractmethod
    def create_company_positions(self, time, company, spot_fx_cache):
        """
        Create all position object for a company.
        """
        pass

    @abstractmethod
    def create_company_cash_positions(self, time, company):
        pass

    @abstractmethod
    def create_company_fx_positions(self, time, company, spot_fx_cache):
        """
        TODO: Test for when a broker closes all positions.
        """
        pass

    @abstractmethod
    def create_fx_positions(self, final_positions, company_event):
        """
        Create account Fx positions Fx position interface objects. This is a simple translation to do, since Fx
        position (DB) objects implement FxPositionInterface.
        """
        pass

    @abstractmethod
    def reconcile_company(self, time, company, spot_cache, callback):
        """
        Reconciliation takes the last and current company positions, along with information about trading and what
        positions the company's accounts want to have and uses it to create the account positions and monitor
        what happened to a company between the initial point and final point.

        Every time account or company positions need to be updated, they need to
        be updated together to maintain coherence.
        """
        pass


class BrokerReconcileService(BrokerReconcileServiceInterface):
    """
    Service responsible for company reconciliation and related functionality, including creating company Fx positions
    from broker information (or fabricating them for DEMO positions) and creating account positions.
    """

    def __init__(self,
                 broker_service: BrokerServiceInterface = BrokerService(),
                 oms_hedge_service: OMSHedgeServiceInterface = OMSHedgeService()):
        self._broker_service = broker_service
        self._oms_hedge_service = oms_hedge_service

    def create_company_positions(self, time: Date, company: Company, spot_fx_cache: SpotFxCache) -> CompanyEvent:
        """
        Create all position object for a company.
        """
        try:
            self.create_company_cash_positions(time=time, company=company)
        except Exception as ex:
            logger.error(f"Error creating company cash positions: {ex}")
        return self.create_company_fx_positions(time=time, company=company, spot_fx_cache=spot_fx_cache)

    def create_company_cash_positions(self, time: Date, company: Company) -> CompanyEvent:
        logger.debug(f"Creating company cash records (cash holdings and accrued cash)")

        cash_holdings_by_broker, accrued_cash_by_broker = self._broker_service.get_cash_holdings(company=company)

        # Create (or get) a company event for this positions snapshot
        event = CompanyEvent.get_or_create_event(company=company, time=time)
        logger.debug(f"Got company event {event.id} for company {company} at time {time}")

        if 0 < len(cash_holdings_by_broker):
            logger.debug(f"Cash holdings by broker for company {company}:")
            for broker_account, cash_holdings in cash_holdings_by_broker.items():
                try:
                    try:
                        if 0 < len(cash_holdings):
                            logger.debug(f"  * Broker '{broker_account}'")
                            for currency, amount in cash_holdings.items():
                                logger.debug(f"     = {currency}: {amount}")
                    except Exception as ex:
                        logger.error(f"Could not print company cash holdings by broker: {ex}")

                    CompanyCashHolding.create_cash_holdings(event, broker_account, cash_holdings)
                except Exception as ex:
                    logger.error(f"Could not create company cash holding for company {company}: {ex}")

            logger.debug(f"Accrued cash by broker for company {company}:")
            for broker_account, accrued_cash in accrued_cash_by_broker.items():
                try:
                    try:
                        if 0 < len(accrued_cash):
                            logger.debug(f"  * Broker '{broker_account}'")
                            for currency, amount in accrued_cash.items():
                                logger.debug(f"     = {currency}: {amount}")
                    except Exception as ex:
                        logger.error(f"Could not print company cash holdings by broker: {ex}")

                    CompanyAccruedCash.create_accrued_cash_record(event, broker_account, accrued_cash)
                except Exception as ex:
                    logger.error(f"Could not create company accrued cash for company {company}: {ex}")
        else:
            logger.debug(f"Company has no cash holdings.")

        return event

    def create_company_fx_positions(self, time: Date, company: Company, spot_fx_cache: SpotFxCache) -> CompanyEvent:
        from ib_insync import Forex
        """
        TODO: Test for when a broker closes all positions.
        """
        logger.debug(f"Creating company positions snapshot for company {company} at reference time {time}.")

        positions_by_broker = self._broker_service.get_account_positions_by_broker(company=company)

        # Get the last live and demo positions. This lets us check whether all positions were closed at any broker.
        last_event, _ = CompanyFxPosition.get_account_positions_by_broker_account(company=company,
                                                                                  time=time)
        last_time = last_event.time if last_event else None

        # A list of broker accounts that currently hold positions. We will check this list against the last_brokers
        # list at the end of the function, and add a zero position for each broker that was in the last brokers list
        # but is not in the current brokers list.
        current_brokers = []

        # Create (or get) a company event for this positions snapshot
        event = CompanyEvent.get_or_create_event(company=company, time=time)

        # Broker account types are live and paper. If there is no paper account, we are just setting the DEMO company
        # account types to have exactly the positions we expect them to have.
        had_demo, had_live = False, False
        for broker_account, positions_from_broker in positions_by_broker.items():
            current_brokers.append(broker_account)

            if broker_account.account_type != BrokerAccount.AccountType.LIVE:
                had_demo = True

            position_map = {}
            for _, pos in positions_from_broker.items():
                for p in pos:
                    if isinstance(p["contract"], Forex):
                        pair = p["FxPair"]
                        avg_cost = p["avgCost"]
                        amount = p["position"]
                        position_map[pair] = (amount, abs(avg_cost * amount))

            CompanyFxPosition.create_company_positions(event=event,
                                                       company=company,
                                                       broker_account=broker_account,
                                                       positions=position_map)
            logger.debug(f"Created company Fx positions for broker account {broker_account} for company {company}, "
                        f"event id = {event.id}, reference time {event.time}")

        # Here, we handle the case (mentioned above) where there is no paper account for demo positions.
        # We check if there *exist* any demo accounts, and if so, we set the positions to be their aggregate positions.
        if not had_demo:
            # For positions held in the "internal broker" (broker = None), we have to synthesize what the company
            # positions due to these accounts would be by taking the last account positions and adding to them
            # any account requests that occurred since the last positions. We can do this because we always simulate
            # demo positions as fully filling.

            demo_positions = self._create_internal_demo_fxpositions(company=company,
                                                                    time=time,
                                                                    last_time=last_time,
                                                                    spot_fx_cache=spot_fx_cache,
                                                                    account_types=[Account.AccountType.DEMO])
            if demo_positions:
                current_brokers += [None]
                # Create company positions.
                CompanyFxPosition.create_company_positions(event=event,
                                                           company=company,
                                                           broker_account=None,
                                                           positions=demo_positions)

                logger.debug(f"Created company Fx positions for demo positions (using broker account = None) "
                            f"for company {company}, event id = {event.id}, reference time {event.time}")

        event.has_company_fx_snapshot = True
        return event

    def _create_internal_demo_fxpositions(self,
                                          company: Company,
                                          time: Date,
                                          last_time: Date,
                                          spot_fx_cache: SpotFxCache,
                                          account_types: List[Account.AccountType] = (Account.AccountType.DEMO,)
                                          ) -> Optional[Dict[FxPair, Tuple[float, float]]]:
        """
        Function called by create_company_fx_positions to create synthetic Fx positions for the positions coming from
        DEMO accounts.
        """
        accounts = list(filter(lambda x: x.type in account_types,
                               Account.get_active_accounts(company=company)))

        if len(accounts) == 0:
            return None

        # Get last positions.
        demo_positions_by_broker, _ = FxPosition.get_positions_for_accounts(time=time, accounts=accounts)
        # Get any requests that have occurred since the last time positions were recorded.
        demo_orders = DemoOrders.get_fills_in_range(company=company, start_time=last_time, end_time=time)

        # Add last hedge positions.
        position_map = {}
        for pos in demo_positions_by_broker:
            pair = pos.fxpair
            current = position_map.setdefault(pair, [0.0, 0.0])  # Amount, total_price
            current[0] += pos.amount
            current[1] += np.sign(pos.amount) * pos.total_price

        # Add changes in hedges due to account hedge requests. We round requests to lot sizes (we simulate fills
        # with valid lot sizes), and simulate the fill price using the spot cache.
        for order in demo_orders:
            fx_pair, filled_amount = order.pair, order.requested_amount
            additional_price = filled_amount * spot_fx_cache.get_fx(fx_pair=fx_pair)

            current = position_map.setdefault(fx_pair, [0.0, 0.0])  # Amount, total_price
            current[0] += filled_amount
            current[1] += additional_price

        # Convert to output form.
        output = {}
        for fx_pair, data in position_map.items():
            output[fx_pair] = (data[0], np.abs(data[1]))  # Total price is always positive.

        return output

    def reconcile_company(self,
                          time: Date,
                          company: Company,
                          spot_cache: SpotFxCache,
                          callback: ReconciliationCallback):
        """
        Reconciliation takes the last and current company positions, along with information about trading and what
        positions the company's accounts want to have and uses it to create the account positions and monitor
        what happened to a company between the initial point and final point.

        Every time account or company positions need to be updated, they need to
        be updated together to maintain coherence.
        """

        logger.debug(f"Starting company reconciliation and position snapshotting for {company}.")

        # Get the last time (strictly less than now, if it matters) that reconciliation occurred for this company.
        last_reconciliation_time = ReconciliationRecord.get_last_reconciliation_time(company=company, time=time)

        if last_reconciliation_time is None:
            logger.debug(f"Cannot find any last reconciliation records for company {company}.")
        else:
            logger.debug(f"The last reconciliation records for company {company} are from {last_reconciliation_time}.")

        # Snapshot the company positions from the broker (and from internal "DEMO" accounts).
        # These are the current company positions.
        event = callback.create_company_positions(company=company, time=time, spot_cache=spot_cache)
        logger.debug(f"Current company positions tied to event id = {event.id}")

        logger.debug("RECONCILING for DEMO accounts.")
        self._reconcile_for_single_type(company=company, time=time, current_event=event,
                                        callback=callback, spot_cache=spot_cache, is_live=False, name="DEMO")
        logger.debug("RECONCILING for LIVE accounts.")
        self._reconcile_for_single_type(company=company, time=time, current_event=event,
                                        callback=callback, spot_cache=spot_cache, is_live=True, name="LIVE")

        logger.debug(f"Done with reconciliation for company '{company}', id = {company.id}")

    def _reconcile_for_single_type(self,
                                   company: Company,
                                   time: Date,
                                   current_event: CompanyEvent,
                                   callback: ReconciliationCallback,
                                   spot_cache: SpotFxCache,
                                   is_live: bool,
                                   name: str):
        # Get the account type enum given "is_live"
        account_type = Account.AccountType.LIVE if is_live else Account.AccountType.DEMO

        # Get the last company positions.
        last_company_positions, last_event = CompanyFxPosition.get_consolidated_positions(company=company, time=time,
                                                                                          live_positions=is_live,
                                                                                          inclusive=False)
        last_reconciliation_time = last_event.time if last_event else None

        # Check on last live positions.
        if last_event is None:
            logger.debug(f"There are no last company {name} positions.")
        else:
            logger.debug(f"Last company {name} positions from event id = {last_event.id}, at time {last_event.time}")
            for fxpair, amount in last_company_positions.items():
                logger.debug(f"  * {fxpair}: {amount}")

        company_positions_event = CompanyEvent.get_event_of_most_recent_positions(time=time, company=company)
        current_company_positions = CompanyFxPosition.get_consolidated_positions_for_event(
            company_event=company_positions_event,
            live_positions=is_live)

        # Check on current positions of this type.
        if len(current_company_positions) == 0:
            logger.debug(f"There are no current company {name} positions.")
        else:
            logger.debug(f"Current company {name} positions (from event {company_positions_event.id}):")
            for fxpair, amount in current_company_positions.items():
                logger.debug(f"  * {fxpair}: {amount}")

        # Stage the data for running the reconciliation calculator.

        def transform(objs) -> Dict[FxPair, List[AccountHedgeRequest]]:
            output = {}
            for obj in objs:
                output.setdefault(obj.pair, []).append(obj)
            return output

        requests = transform(AccountHedgeRequestService.get_account_hedge_requests_in_range(
            company=company,
            start_time=last_reconciliation_time,
            end_time=time,
            is_live=is_live))

        logger.debug(f"Found {len(requests)} {name} account hedge requests for company {company}, time window between "
                    f"{last_reconciliation_time} and {time}.")

        # Get the most recent Account positions.
        account_positions, account_pos_event = FxPosition.get_positions_per_account_per_fxpair(
            company=company, time=time,
            account_type=account_type,
            inclusive=False)

        # Get the account desired positions.
        account_desired_positions = AccountDesiredPositions.get_desired_positions_by_fx(company=company,
                                                                                        time=time,
                                                                                        live_only=is_live,
                                                                                        inclusive=False)

        # Log the account positions. By nature of the query, there can't be a separate event for LIVE and DEMO.
        if account_pos_event:
            logger.debug(f"Account positions are from event {account_pos_event.id} at time {account_pos_event.time}")
            if last_event != account_pos_event:
                logger.warning(f"Note that account positions and company positions are not tied to the same "
                               f"company event.")
        else:
            logger.debug(f"No previous account positions, no event for account positions.")

        if len(account_positions) == 0:
            logger.debug(f"No {name} account positions.")
        else:
            self._print_account_positions(account_positions=account_positions, name=name)

        actions = list(CompanyHedgeAction.get_actions(company=company,
                                                      start_time=last_reconciliation_time,
                                                      end_time=time))
        if 1 < len(actions):
            logger.warning(f"We expect there to be at most one company hedge action between "
                           f"reconciliations / position snapshotting. There are {len(actions)}.")
            # TODO: Raise error? What to do here?

        if len(actions) == 1:
            filled_amounts = self._oms_hedge_service.get_filled_amount_per_fx_pair_for_company(
                company_hedge_action=actions[0],
                account_type=account_type,
                spot_cache=spot_cache)
        else:
            filled_amounts = None

        reconciliation = ReconciliationCalculator()

        # Reconcile positions.
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            reconciliation.reconcile_company(company_positions_before=last_company_positions,
                                             company_positions_after=current_company_positions,
                                             account_desired_positions=account_desired_positions,
                                             initial_account_positions=account_positions,
                                             account_hedge_requests=requests,
                                             filled_amounts=filled_amounts,
                                             spot_cache=spot_cache)
        # Set filled positions and set domestic PnL.
        self._handle_results(account_hedge_results=account_hedge_results,
                             spot_cache=spot_cache, company=company, callback=callback)

        if 0 < len(account_positions) or 0 < len(account_hedge_results):
            logger.debug(f"Creating {name} FxPositions for {len(account_hedge_results)} positions.")
            callback.create_fx_positions(final_positions_by_fxpair, company_event=current_event)
        # Store reconciliation date.
        callback.create_reconciliation_records(company=company, time=time, reconciliation_data=reconciliation_data,
                                               is_live=is_live)

        logger.debug(f"Done with reconciliation for {name} accounts.")

    def _handle_results(self, account_hedge_results, spot_cache, company, callback: ReconciliationCallback):
        if 0 < len(account_hedge_results):
            for result in account_hedge_results:
                # Handle the result - potentially update or save.
                callback.update_hedge_result(result)

    def create_fx_positions(self,
                            final_positions: Dict[FxPairInterface, Dict[AccountInterface, FxPositionInterface]],
                            company_event: CompanyEvent) -> List[FxPosition]:
        """
        Create account Fx positions Fx position interface objects. This is a simple translation to do, since Fx
        position (DB) objects implement FxPositionInterface.
        """
        # Create Fx positions.
        new_positions = []
        logger.debug(f"Creating FX positions for company {company_event.company}, company event {company_event.id}.")
        for fxpair, positions_by_account in final_positions.items():
            for account, basic_fx_position in positions_by_account.items():
                if basic_fx_position.get_amount() != 0:
                    amount = basic_fx_position.get_amount()

                    # If the amount size is tiny, don't set a position.
                    if np.abs(amount) < 1.e-4:
                        logger.warning(f"Position amount (absolute) of {fxpair} for account {account} is < 1.e-4 in "
                                       f"magnitude, not setting position")
                        continue

                    # If the amount is NaN, log an error and do not set a position.
                    if np.isnan(amount):
                        logger.error(f"Amount of {fxpair} for account {account} is NaN. Not setting this position.")
                        # TODO: This is really a problem, maybe Pub/Sub this?
                        continue

                    px = np.abs(basic_fx_position.get_total_price())
                    # Stop some NaNs from occurring.
                    if np.isnan(px):
                        logger.error("Price of position is NaN - please investigate. Setting price to zero.")
                        px = 0.0

                    new_positions.append(FxPosition(account=account,
                                                    fxpair=fxpair,
                                                    amount=amount,
                                                    company_event=company_event,
                                                    # Total price is always positive (by convention). Guard against a
                                                    # bad implementation of an FX position by taking ABS.
                                                    total_price=px))
                    logger.debug(f"  * Adding FX position: Account = {account}, FX = {fxpair}, "
                                f"Amount = {basic_fx_position.get_amount()}, "
                                f"Total Px = {np.abs(basic_fx_position.get_total_price())}")
                else:
                    logger.warning(f"  * Amount for FX position for Account = {account}, "
                                   f"FX = {fxpair} was zero, not setting a position.")

        logger.debug(f"Creating {len(new_positions)} positions for company event id = {company_event.id}.")
        positions = FxPosition.objects.bulk_create(new_positions)

        # There are account positions. There may actually be no FxPosition objects created, indicating that positions
        # were zero or closed, but the set of position (possibly the empty set) associated with this even is an
        # accurate depiction of what the accounts' positions were at this time.
        if not company_event.has_account_fx_snapshot:
            company_event.has_account_fx_snapshot = True
            company_event.save()
        # Return the created positions.
        return positions

    @staticmethod
    def _print_account_positions(account_positions, name: str):
        if len(account_positions) == 0:
            logger.debug(f"No {name} account positions.")
        else:
            logger.debug(f"{name} Account positions per Fx pair:")
            for fxpair, pos_per_account in account_positions.items():
                logger.debug(f"  * {fxpair}:")
                for account, fx_position in pos_per_account.items():
                    logger.debug(f"    - "
                                f"Account = '{fx_position.get_account()}', "
                                f"Amount = {fx_position.get_amount()}, "
                                f"Px = {fx_position.get_total_price()}")


class BacktestBrokerReconcileService(BrokerReconcileService):
    def __init__(self,
                 broker_service: BrokerServiceInterface,
                 oms_hedge_service: OMSHedgeServiceInterface, ):
        super().__init__(broker_service=broker_service,
                         oms_hedge_service=oms_hedge_service)

    def create_company_fx_positions(self, time: Date, company: Company, spot_fx_cache: SpotFxCache) -> CompanyEvent:
        """
        TODO: Test for when a broker closes all positions.
        """
        logger.debug(f"Creating company positions snapshot for company {company} at reference time {time}.")

        # Get the last live and demo positions. This lets us check whether all positions were closed at any broker.
        last_event, _ = CompanyFxPosition.get_account_positions_by_broker_account(company=company,
                                                                                  time=time)
        last_time = last_event.time if last_event else None

        # Create (or get) a company event for this positions snapshot
        event = CompanyEvent.get_or_create_event(company=company, time=time)

        # For positions held in the "internal broker" (broker = None), we have to synthesize what the company
        # positions due to these accounts would be by taking the last account positions and adding to them
        # any account requests that occurred since the last positions. We can do this because we always simulate
        # demo positions as fully filling.
        demo_positions = self._create_internal_demo_fxpositions(company=company,
                                                                time=time,
                                                                last_time=last_time,
                                                                spot_fx_cache=spot_fx_cache,
                                                                account_types=[Account.AccountType.DEMO,
                                                                               Account.AccountType.LIVE])
        if demo_positions:
            # Create company positions.
            CompanyFxPosition.create_company_positions(event=event,
                                                       company=company,
                                                       broker_account=company.broker_accounts.first(),
                                                       positions=demo_positions)

            logger.debug(f"Created company Fx positions for demo positions (using broker account = None) "
                        f"for company {company}, event id = {event.id}, reference time {event.time}")

        event.has_company_fx_snapshot = True
        return event

    def _create_internal_demo_fxpositions(self,
                                          company: Company,
                                          time: Date,
                                          last_time: Date,
                                          spot_fx_cache: SpotFxCache,
                                          account_types=None
                                          ) -> Optional[Dict[FxPair, Tuple[float, float]]]:
        """
        Function called by create_company_fx_positions to create synthetic Fx positions for the positions coming from
        DEMO accounts.
        """
        if account_types is None:
            account_types = [Account.AccountType.DEMO]

        accounts = list(filter(lambda x: x.type in account_types,
                               Account.get_active_accounts(company=company)))

        if len(accounts) == 0:
            return None

        # Get last positions.
        demo_positions_by_broker, _ = FxPosition.get_positions_for_accounts(time=time, accounts=accounts)
        hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company, time=time)
        if not hedge_action:
            return {}
        orders = self._oms_hedge_service.get_filled_amount_per_fx_pair_for_company(company_hedge_action=hedge_action,
                                                                                   account_type=Account.AccountType.LIVE,
                                                                                   spot_cache=spot_fx_cache)

        # Add last hedge positions.
        position_map = {}
        for pos in demo_positions_by_broker:
            pair = FxPair.get_pair(pos.fxpair)
            current = position_map.setdefault(pair, [0.0, 0.0])  # Amount, total_price
            current[0] += pos.amount
            current[1] += np.sign(pos.amount) * pos.total_price

        # Add changes in hedges due to account hedge requests. We round requests to lot sizes (we simulate fills
        # with valid lot sizes), and simulate the fill price using the spot cache.
        for pair, order in orders.items():
            pair = FxPair.get_pair(pair)
            current = position_map.setdefault(pair, [0.0, 0.0])  # Amount, total_price
            current[0] += order.amount_filled
            current[1] += np.sign(order.amount_filled) * order.average_price

        # Convert to output form.
        output = {}
        for fx_pair, data in position_map.items():
            output[fx_pair] = (data[0], np.abs(data[1]))  # Total price is always positive.

        return output
