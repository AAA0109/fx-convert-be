import bisect
from typing import Optional, Dict, List, Union, Iterable

import numpy as np
from hdlib.Instrument.CashFlow import CashFlow
from hdlib.Universe.Pricing.CashFlowPricer import CashFlowPricer
from hdlib.Universe.Universe import Universe

from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.CompanyInterface import CompanyInterface
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from main.apps.account.models import Company, Account
from main.apps.broker.models import Broker
from main.apps.account.services.cashflow_provider import CashFlowProviderService
from main.apps.auditing.support.CompanyTimeline import CompanyTimeline
from main.apps.currency.models import FxPair, Currency
from main.apps.hedge.calculators.RatesCache import BrokerRatesCaches
from main.apps.hedge.calculators.company_hedge import CompanyHedgeCallback
from main.apps.hedge.calculators.liquidity_adjust import get_liquidity_adjusted_positions
from main.apps.hedge.models import CompanyHedgeAction, FxPosition, AccountHedgeRequest, OMSOrderRequest, CompanyEvent, \
    AccountDesiredPositions, HedgeSettings
from main.apps.hedge.models.company_fxposition import CompanyFxPosition
from main.apps.hedge.services.cost import CostProviderService
from main.apps.hedge.services.hedger import hedge_company
from main.apps.hedge.services.oms import OMSHedgeService
from main.apps.history.models import AccountSnapshot
from main.apps.history.services.snapshot import SnapshotCreatorService
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.oems.services.order_service import OrderService

import logging

logger = logging.getLogger(__name__)


class AuditCallback(CompanyHedgeCallback):
    def set_company_hedge_action(self, company_hedge_action):
        self._company_hedge_action = company_hedge_action

    def notify_account_position_changes(self, live_changes: Dict[AccountInterface, PositionChange],
                                        demo_changes: Dict[AccountInterface, PositionChange]):
        if 0 < len(live_changes):
            logger.debug(f"Live changes:")
            for account, change in live_changes.items():
                if change.has_changes:
                    logger.debug(f"  * {account}: {change}")
                else:
                    logger.debug(f"  * {account}: No change")
        else:
            logger.debug(f"No live changes.")
        if 0 < len(demo_changes):
            logger.debug(f"Demo changes:")
            for account, change in demo_changes:
                if change.has_changes:
                    logger.debug(f"  * {account}: {change}")
                else:
                    logger.debug(f"  * {account}: No change")
        else:
            logger.debug(f"No demo changes.")

    def notify_aggregated_changes(self, company: CompanyInterface, agg_live_changes: PositionChange,
                                  agg_demo_changes: PositionChange):
        logger.debug(f"Aggregated live changes: {agg_live_changes}")
        logger.debug(f"Aggregated demo changes: {agg_demo_changes}")

    def apply_liquidity_changes(self,
                                live_account_exposures: Dict[FxPair, Dict[Account, float]],
                                demo_account_exposures: Dict[FxPair, Dict[Account, float]],
                                live_liquidity_changes: Dict[FxPair, float],
                                demo_liquidity_changes: Dict[FxPair, float],
                                ):
        if self._company_hedge_action is None:
            return

        live_desired_positions = AccountDesiredPositions.get_desired_positions_by_fx(
            hedge_action=self._company_hedge_action,
            live_only=True)
        live_position_adjustments = get_liquidity_adjusted_positions(account_exposures=live_account_exposures,
                                                                     desired_positions=live_desired_positions,
                                                                     liquidity_changes=live_liquidity_changes)
        # The live_positions_adjustments is covariant, but the type checker still complains, so I'm suppressing it.
        # noinspection PyTypeChecker

        demo_desired_positions = AccountDesiredPositions.get_desired_positions_by_fx(
            hedge_action=self._company_hedge_action,
            live_only=False)
        demo_position_adjustments = get_liquidity_adjusted_positions(account_exposures=demo_account_exposures,
                                                                     desired_positions=demo_desired_positions,
                                                                     liquidity_changes=demo_liquidity_changes)


class CashflowValuesDelta:
    def __init__(self,
                 cashflow: CashFlow,
                 initial_spot: float, final_spot: float,
                 initial_Z: float, final_Z: float,
                 init_fwd: float, final_fwd: float,
                 init_npv: float, final_npv: float):
        self.cashflow = cashflow
        self.initial_spot = initial_spot
        self.final_spot = final_spot
        self.initial_Z = initial_Z
        self.final_Z = final_Z
        self.init_fwd = init_fwd
        self.final_fwd = final_fwd
        self.initial_npv = init_npv
        self.final_npv = final_npv

    def change_in_npv(self):
        return self.final_npv - self.initial_npv

    def change_in_fwd(self):
        return self.final_fwd - self.init_fwd

    def change_in_spot(self):
        return self.initial_spot - self.final_spot


class CashFlowComparer:
    """
    Object that helps explain how the value of a single set of cashflows changed between an initial and final point
    in time.
    """

    def __init__(self, initial_universe: Universe, final_universe: Universe):
        self._initial_universe = initial_universe
        self._final_universe = final_universe

        self._initial_pricer = CashFlowPricer(self._initial_universe)
        self._final_pricer = CashFlowPricer(self._final_universe)

    def explain_cashflow_value_summary(self,
                                       cashflows: Iterable[CashFlow],
                                       value_currency: Currency) -> List[CashflowValuesDelta]:
        output = []
        for cashflow in cashflows:
            # Spot Value
            init_spot_value = self._initial_pricer.convert_cashflow_at_spot(cash=cashflow,
                                                                            value_currency=value_currency)
            final_spot_value = self._final_pricer.convert_cashflow_at_spot(cash=cashflow,
                                                                           value_currency=value_currency)

            # Forward Value
            init_fwd_value = self._initial_pricer.convert_cashflow_forward(cash=cashflow,
                                                                           value_currency=value_currency)
            final_fwd_value = self._final_pricer.convert_cashflow_forward(cash=cashflow, value_currency=value_currency)

            # Net Present Value (NPV)

            Zi = self._initial_universe.get_discount(asset=value_currency, date=cashflow.pay_date)
            Zf = self._final_universe.get_discount(asset=value_currency, date=cashflow.pay_date)

            init_npv = Zi * init_fwd_value
            final_npv = Zf * final_fwd_value

            output.append(CashflowValuesDelta(cashflow, init_spot_value, final_spot_value,
                                              Zi, Zf,
                                              init_fwd_value, final_fwd_value,
                                              init_npv, final_npv))
        return output


class AuditingService:
    @staticmethod
    def audit_company(company: Company,
                      start_time: Optional[Date] = None,
                      end_time: Optional[Date] = None,
                      do_corrections: bool = False,
                      live_positions: bool = True):
        account_positions = FxPosition.get_positions_by_event_and_account(company=company)

        account_hedge_requests = AccountHedgeRequest.get_hedge_requests_by_action_and_account(company=company,
                                                                                              start_date=start_time,
                                                                                              end_date=end_time)

        company_fx_positions = CompanyFxPosition.get_consolidated_positions_by_snapshot(company=company,
                                                                                        start_time=start_time,
                                                                                        end_time=end_time,
                                                                                        live_positions=live_positions)

        oms_requests = OMSOrderRequest.get_requests_by_event(company=company, start_time=start_time, end_time=end_time)

        timeline = CompanyTimeline(company=company,
                                   account_positions=account_positions,
                                   account_hedge_requests=account_hedge_requests,
                                   company_fx_positions=company_fx_positions,
                                   oms_requests=oms_requests)

        logger.debug(f"Writing history for company \"{company}\", id = {company.id}.\n\n")

        current_company_positions = None
        current_account_positions = None

        last_time = None

        timeline_pairs = sorted([(event.time, plot_point) for event, plot_point in timeline.plot.items()],
                                key=lambda x: x[0])

        for it in range(len(timeline_pairs)):
            time, plot_point = timeline_pairs[it]

            logger.debug(f"=========================================")
            if last_time:
                logger.debug(f"Time: {time}, Difference from last: {time - last_time}")
            else:
                logger.debug(f"Time: {time}")
            last_time = time

            if plot_point.company_event is not None:
                logger.debug(f"  * Company event = {plot_point.company_event.id}")
            if plot_point.company_hedge_actions is not None:
                if len(plot_point.company_hedge_actions) == 1:
                    logger.debug(f"  * There was one company hedge action: {plot_point.company_hedge_actions[0].id}")
                else:
                    ids = [action.id for action in plot_point.company_hedge_actions]
                    logger.debug(f"  * There were {len(plot_point.company_hedge_actions)} company hedge actions: {ids}")

            if plot_point.company_fx_positions:
                current_company_positions = plot_point.company_fx_positions
            if plot_point.account_positions:
                current_account_positions = plot_point.account_positions

            # =============================================================================================
            #  Account hedge requests.
            # =============================================================================================

            if plot_point.account_hedge_requests is not None:
                logger.debug(f"Account hedge requests: ")
                total_requests, total_filled = {}, {}
                for account, requests in sorted(plot_point.account_hedge_requests.items()):
                    logger.debug(f"  * Account = {account} (id = {account.id})")
                    for request in sorted(requests, key=lambda r: r.pair):

                        # Only display requests with nonzero amount requested.
                        if request.requested_amount == 0:
                            continue

                        logger.debug(
                            f"      {request.pair} [id={request.id}]: amount requested = {request.requested_amount}, "
                            f"filled = {request.filled_amount}, "
                            f"px = {request.price[0]}, "
                            f"pnl (domestic) = {request.realized_pnl_domestic} "
                            f"[ref time = {request.company_hedge_action.time}, "
                            f"action id = {request.company_hedge_action.id}]")

                        total_requests[request.pair] = total_requests.setdefault(request.pair, 0) \
                                                       + request.requested_amount
                        total_filled[request.pair] = total_requests.setdefault(request.pair, 0) \
                                                     + request.filled_amount if request.filled_amount else 0.
                logger.debug(f"  == Request summary ==")
                for pair in sorted(total_requests.keys()):
                    logger.debug(f"  * {pair}: requests = {total_requests[pair]}, filled = {total_filled[pair]}")
            else:
                logger.debug(f"Account hedge requests: None")

            # =============================================================================================
            #
            # =============================================================================================

            if plot_point.oms_requests is not None:
                logger.debug(f"OMS Requests: ({len(plot_point.oms_requests)})")
                for request in plot_point.oms_requests:
                    request: OMSOrderRequest = request
                    logger.debug(f"  * {request.pair}: amount requests = {request.requested_amount}, "
                                f"filled = {request.filled_amount}, "
                                f"px = {request.total_price}, "
                                f"status = {request.print_status}")
            else:
                logger.debug(f"OMS Requests: None")

            # =============================================================================================
            #  Account Fx positions
            # =============================================================================================

            has_account_positions, has_nan_total_prices = False, False
            total_positions, total_price = {}, {}
            if current_account_positions is not None:
                logger.debug(f"Account positions: ")

                for account, positions in sorted(current_account_positions.items()):
                    logger.debug(f"  * Account = {account} (id = {account.id})")
                    for pos in sorted(positions, key=lambda p: p.fxpair):
                        if pos.amount == 0:
                            logger.debug(f"      [{pos.fxpair}: Zero]")
                            continue
                        logger.debug(f"      {pos.fxpair}: {pos.amount}, px = {pos.total_price} "
                                    f"[time = {pos.company_event.time}, fx pos id = {pos.id}]")
                        total_positions[pos.fxpair] = total_positions.get(pos.fxpair, 0.0) + pos.amount
                        total_price[pos.fxpair] = total_price.get(pos.fxpair, 0.0) \
                                                  + pos.total_price * np.sign(pos.amount)

                logger.debug(f" == Positions summary ==")
                for fx_pair in sorted(total_positions.keys()):
                    has_account_positions = True
                    has_nan_total_prices |= np.isnan(total_price[fx_pair])
                    logger.debug(f"  * {fx_pair}: {total_positions[fx_pair]}, px = {np.abs(total_price[fx_pair])}")
            else:
                logger.debug(f"Account positions: None")

            # =============================================================================================
            #  Company Fx positions
            # =============================================================================================

            if current_company_positions is None:
                logger.debug(f"Company Positions: None")
                if has_account_positions:
                    # Check future plot points to see if the snapshots there recorded the positions.
                    next_company_positions, next_time = None, None
                    dit = 1
                    while it + dit < len(timeline_pairs) and next_company_positions is None:
                        next_time, next_plot_point = timeline_pairs[it + dit]
                        next_company_positions = next_plot_point.company_fx_positions
                        dit += 1
                    if next_company_positions is not None:
                        # current_company_positions = next_company_positions
                        # logger.debug(f"Getting next company positions, which came from time {next_time} "
                        #             f"({dit - 1} points in the future):")
                        pass
            if current_company_positions:
                logger.debug(f"Company Positions:")
                AuditingService._print_company_positions(current_company_positions)
            else:
                logger.debug(f"Company Positions: None")

            if has_nan_total_prices and current_company_positions is not None and do_corrections:
                logger.debug(f"Correcting NaN total prices in account hedge positions...")
                for fx_pair, px in total_price.items():
                    if np.isnan(px):  # Needs to be corrected.
                        amount, px = current_company_positions.get(fx_pair, [0.0, 0.0])
                        ratio = total_positions[fx_pair] / amount

                        if 0.01 < np.abs(1. - ratio):
                            logger.warning(
                                f"Account's record of total positions does not match with company positions!")
                            continue
                        avg_px = px / amount

                        for account, positions in current_account_positions.items():
                            for pos in positions:
                                if pos.fxpair != fx_pair or pos.amount == 0.0:
                                    continue
                                new_total_px = np.abs(ratio * avg_px * pos.amount)
                                logger.debug(f"  -> Setting account '{account}' pair {fx_pair} (amount {pos.amount}) "
                                            f"price to be {new_total_px}, was {pos.total_price}.")
                                # Set and save the new price.
                                pos.total_price = new_total_px
                                pos.save()

            logger.debug(f"=========================================\n")

        pass

    @staticmethod
    def replay_hedge(company_hedge_action_id: int):
        action = CompanyHedgeAction.get_action(company_hedge_action_id)

        company = action.company
        hedge_time = Date.from_datetime(action.time)
        market_converter = FxMarketConventionService().make_fx_market_converter()

        universe = UniverseProviderService().make_cntr_currency_universe(domestic=company.currency,
                                                                         ref_date=hedge_time,
                                                                         bypass_errors=True)

        cost_provider = CostProviderService().get_cost_provider(date=hedge_time, fx_cache=universe,
                                                                domestic=company.currency,
                                                                broker="IBKR")

        callback = AuditCallback()
        callback.set_company_hedge_action(company_hedge_action=action)
        hedge_company(hedge_time=hedge_time,
                      company_hedge_action=action,
                      hedge_account_types=OMSHedgeService.hedgeable_account_types,
                      cost_provider=cost_provider,
                      universe=universe,
                      market_converter=market_converter,
                      callback=callback)

    @staticmethod
    def changes_explained_for_snapshot(snapshot: Union[AccountSnapshot, int]):
        if isinstance(snapshot, AccountSnapshot):
            snapshot_ = snapshot
        else:
            snapshot_ = AccountSnapshot.objects.get(pk=snapshot)

        # Find the last hedge action.
        hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=snapshot_.account.company)
        if hedge_action:
            AuditingService.changes_explained(hedge_action)

    @staticmethod
    def changes_explained(ending_company_hedge_action: CompanyHedgeAction):
        logger.debug("")
        logger.debug(f"Explaining changes for (ending) company hedge action {ending_company_hedge_action.id}, "
                    f"time {ending_company_hedge_action.time}")

        company = ending_company_hedge_action.company
        ending_time = Date.from_datetime(ending_company_hedge_action.time)
        previous_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company,
                                                                             time=ending_time,
                                                                             inclusive=False)
        if not previous_action:
            logger.warning(f"There is no previous company hedge action before {ending_company_hedge_action.id}.")
            return
        starting_time = Date.from_datetime(previous_action.time)

        # Get the company events that have the position snapshots. There should be one just after the first
        # action and one just before the second action.
        events = CompanyEvent.get_events_in_range(company=company,
                                                  start_time=starting_time,
                                                  end_time=ending_time,
                                                  lower_inclusive=False,
                                                  upper_inclusive=True)
        events = list(sorted(list(events), key=lambda x: x.time))
        if len(events) < 2:
            logger.warning(f"Expected at least two CompanyEvents in the range ({starting_time}, {ending_time}), "
                           f"found {len(events)}.")
            return

        first_event, last_event = events[0], events[-1]
        logger.debug(
            f"Events were {first_event.id} at {first_event.time} and {last_event.id} at time {last_event.time}")

        # FX converter can change data into market convention.
        converter = FxMarketConventionService().make_fx_market_converter()
        spot_cache = FxSpotProvider().get_spot_cache(time=starting_time)

        all_accounts = Account.get_account_objs(company=company)
        initial_exposures_per_account = {}
        for account in all_accounts:
            exposures = CashFlowProviderService().get_cash_exposures_for_account(time=starting_time, account=account)
            exposures = exposures.net_exposures()

            # Exposures always have domestic as the quote currency, which may not be the market convention. Change
            # to market convention.
            exposures = converter.convert_positions_to_market(fx_positions=exposures, fx_cache=spot_cache)

            initial_exposures_per_account[account] = exposures

        positions_per_event = FxPosition.get_positions_per_event_per_account(company=company,
                                                                             start_date=first_event.time,
                                                                             end_date=last_event.time)
        first_positions = positions_per_event.get(first_event, {})
        last_positions = positions_per_event.get(last_event, {})

        # Get all trades that occurred during the time period.

        for account in all_accounts:
            net_exposures = initial_exposures_per_account.get(account, {})
            if net_exposures is None:
                logger.debug(f"No exposures for account {account}")
                continue
            logger.debug(f"Exposures and positions for account {account}")

            positions = first_positions.get(account, {})
            final_positions = last_positions.get(account, {})

            all_fxpairs = set(net_exposures.keys())
            positions_per_fx, final_positions_per_fx = {}, {}
            for pos in positions:
                all_fxpairs.add(pos.fxpair)
                positions_per_fx[pos.fxpair] = pos
            for pos in final_positions:
                all_fxpairs.add(pos.fxpair)
                final_positions_per_fx[pos.fxpair] = pos

            for fxpair in all_fxpairs:
                exposure_amount = net_exposures.get(fxpair, 0.)
                position = positions_per_fx.get(fxpair, None)
                position = position.amount if position else 0.
                final_pos = final_positions_per_fx.get(fxpair, None)
                final_pos = final_pos.amount if position else 0.
                logger.debug(f"  * {fxpair}: Exposure = {exposure_amount}, "
                            f"FxPosition = {position:.3f} (final pos = {final_pos:.3f}) => "
                            f"(ratio {-position / exposure_amount if exposure_amount != 0 else 'undef'})")

    @staticmethod
    def account_value_change_explained_snapshots(ending_snapshot):
        snapshot_ = AccountSnapshot.get_snapshot(ending_snapshot)
        last_snapshot = snapshot_.last_snapshot
        AuditingService.account_value_change_explained(account=snapshot_.account,
                                                       start_time=Date.from_datetime(last_snapshot.snapshot_time),
                                                       end_time=Date.from_datetime(snapshot_.snapshot_time))

    @staticmethod
    def account_value_change_explained(account: Account, start_time: Date, end_time: Date):
        # starting_cashflows = AuditingService.get_cashflows_in_range(account=account, time=start_time)
        ending_cashflows = AuditingService.get_cashflows_in_range(account=account, time=end_time)

        domestic = account.company.currency

        initial_positions = FxPosition.get_position_objs(account=account, time=start_time)
        final_positions = FxPosition.get_position_objs(account=account, time=start_time)



        initial_universe = AuditingService.make_universe(time=start_time, domestic=domestic)
        final_universe = AuditingService.make_universe(time=end_time, domestic=domestic)
        comparer = CashFlowComparer(initial_universe=initial_universe, final_universe=final_universe)
        comparison = comparer.explain_cashflow_value_summary(cashflows=ending_cashflows, value_currency=domestic)
        pass

    @staticmethod
    def get_cashflows_in_range(account: Account, time: Date):
        hedge_settings = HedgeSettings.get_hedge_settings(account)
        if not hedge_settings:
            return []
        max_horizon = min(hedge_settings.max_horizon_days if hedge_settings else 365, 10 * 365 + 1)

        return CashFlowProviderService().get_active_cashflows(start_date=time, account=account, inclusive=False,
                                                              max_days_away=max_horizon,
                                                              include_end=True)

    @staticmethod
    def make_universe(time: Date, domestic: Currency):
        service = UniverseProviderService()
        universe = service.make_cntr_currency_universe(domestic=domestic,
                                                       ref_date=time,
                                                       create_vols=False,
                                                       create_corr=False,
                                                       bypass_errors=True)
        return universe

    @staticmethod
    def recreate_snapshot(snapshot_id: int) -> Optional[AccountSnapshot]:
        try:
            snapshot = AccountSnapshot.objects.get(id=snapshot_id)
        except Exception:
            logger.error(f"Could not find snapshot with id {snapshot_id}.")
            return None
        time = Date.from_datetime(snapshot.snapshot_time)
        return AuditingService.regenerate_snapshot(account=snapshot.account, time=time)

    @staticmethod
    def create_snapshot_creator_for_time(time: Date):
        return SnapshotCreatorService(universes=AuditingService._load_universes(time=time),
                                      rates_caches=AuditingService._create_rates_caches(time=time))

    @staticmethod
    def regenerate_snapshot(account: Account, time: Date) -> Optional[AccountSnapshot]:
        service = AuditingService.create_snapshot_creator_for_time(time)
        return service.generate_snapshot(account=account)

    @staticmethod
    def _print_company_positions(company_positions):
        for fx_pair, data in sorted(company_positions.items()):
            logger.debug(f"  * {fx_pair}: {data[0]}, px = {data[1]}")

    @staticmethod
    def _load_universes(time: Date):
        # Loads a universe for every supported domestic currency (currently just USD)
        try:
            # In the future, we load for a set of specified domestics
            usd = Currency.get_currency("USD")
            return UniverseProviderService().make_cntr_currency_universes_by_domestic(
                domestics={usd}, ref_date=time, bypass_errors=True, all_or_none=False)
        except Exception:
            return None

    @staticmethod
    def _create_rates_caches(time: Date) -> BrokerRatesCaches:
        try:
            brokers = Broker.objects.all()
            return CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
        except Exception as e:
            logger.error(f"Error loading broker rates caches: {e}")
            return BrokerRatesCaches()
