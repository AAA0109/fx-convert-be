from typing import Optional, Sequence, Dict, Tuple

import numpy as np
import pandas as pd
import logging

from django.db.models import Min, Max
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Universe.Universe import Universe
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from main.apps.account.models import Company, Account, Currency, CashFlow
from main.apps.broker.models import BrokerAccount
from main.apps.account.services.cashflow_pricer import CashFlowPricerService, CashflowValueSummary
from main.apps.hedge.calculators.RatesCache import BrokerRatesCaches
from main.apps.hedge.calculators.cost import RollCostCalculator, StandardRollCostCalculator
from main.apps.hedge.models import CompanyHedgeAction, HedgeSettings, FxPosition
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.broker import BrokerService
from main.apps.hedge.services.company_position import CompanyPositionsService
from main.apps.hedge.services.cost import CostProviderService
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.services.pnl import PnLProviderService, PnLData
from main.apps.history.models.snapshot import CompanySnapshot, AccountSnapshot
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.hedge.services.margin import MarginCalculator_UnivariateGaussian
from main.apps.history.services.snapshot_provider import SnapshotProvider

logger = logging.getLogger(__name__)


class SnapshotCreatorService(object):
    def __init__(self,
                 universes: Dict[Currency, Universe],
                 rates_caches: BrokerRatesCaches,
                 snapshot_provider: SnapshotProvider = SnapshotProvider(),
                 account_hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService(),
                 broker_service: BrokerService = BrokerService(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 universe_provider_service: UniverseProviderService = UniverseProviderService(),
                 roll_cost_calculator: RollCostCalculator = StandardRollCostCalculator(),
                 cost_provider_service: CostProviderService = CostProviderService()
                 ):
        """
        Service for Creating Company and account snapshots
        :param universes: Universe objects by domestic currency, the financial universes in each counter - currency
        """
        self._ref_date = Date.to_date(next(iter(universes.values())).ref_date)  # Get the ref date from some universe.
        self._universes = universes
        self._last_universes = {}
        self._rates_caches = rates_caches

        self._snapshot_provider = snapshot_provider
        self._account_hedge_request_service = account_hedge_request_service
        self._broker_service = broker_service
        self._hedge_position_service = hedge_position_service
        self._universe_provider_service = universe_provider_service
        self._pnl_provider = PnLProviderService(fx_spot_provider=self._universe_provider_service.fx_spot_provider)
        self._cashflow_pricer = CashFlowPricerService(universe_provider_service=self._universe_provider_service)
        self._roll_cost_calculator = roll_cost_calculator
        self._cost_provider_service = cost_provider_service

        self._dc = DayCounter_HD()

    def set_time(self, time):
        self._ref_date = time

    def create_full_snapshot_for_company(self, company: Company):
        """
        Creates the full snapshot for a company and all its accounts for use in EOD snapshot,
            as of the ref date of this service
        :param company: Company
        """
        self._create_account_snapshots(company=company)
        # Company snapshot should be created after all the company snapshots are created.
        self._create_company_snapshot(company=company)

    def _create_company_snapshot(self, company: Company) -> Optional[CompanySnapshot]:
        universe = self._universes.get(company.currency)

        # Get the last snapshot, if there is any.
        last_snapshot = self._snapshot_provider.get_last_company_snapshot(company=company, date=self._ref_date)
        last_snapshot_date = Date.from_datetime(last_snapshot.snapshot_time) if last_snapshot else None

        # Create a snapshot.
        company_snapshot = CompanySnapshot.create_snapshot(company=company, time=self._ref_date)

        company_snapshot.last_snapshot = last_snapshot
        if last_snapshot:
            last_snapshot.next_snapshot = company_snapshot
            last_snapshot.save()

        # Compute the day-over-day change in PnL and total PnL.
        if last_snapshot:
            # Live Accounts
            live_change_in_realized_pnl = self._pnl_provider.get_realized_pnl(company=company,
                                                                              start_date=last_snapshot_date,
                                                                              end_date=self._ref_date,
                                                                              account_types=(
                                                                                  Account.AccountType.LIVE,),
                                                                              include_start_date=False,
                                                                              spot_fx_cache=universe).total_pnl

            # Note: we subtract the last snapshots change in realized to avoid double counting
            live_total_realized_pnl = live_change_in_realized_pnl + last_snapshot.live_total_realized_pnl

            # Demo Accounts
            demo_change_in_realized_pnl = self._pnl_provider.get_realized_pnl(company=company,
                                                                              start_date=last_snapshot_date,
                                                                              end_date=self._ref_date,
                                                                              account_types=(
                                                                                  Account.AccountType.DEMO,),
                                                                              include_start_date=False,
                                                                              spot_fx_cache=universe).total_pnl

            demo_total_realized_pnl = demo_change_in_realized_pnl + last_snapshot.demo_total_realized_pnl
        else:
            live_change_in_realized_pnl, live_total_realized_pnl = 0.0, 0.0
            demo_change_in_realized_pnl, demo_total_realized_pnl = 0.0, 0.0

        company_snapshot.live_total_realized_pnl = live_total_realized_pnl
        company_snapshot.live_change_in_realized_pnl = live_change_in_realized_pnl

        company_snapshot.demo_total_realized_pnl = demo_total_realized_pnl
        company_snapshot.demo_change_in_realized_pnl = demo_change_in_realized_pnl

        # ==========================
        # Live Broker summary
        # ==========================
        try:
            live_broker_summary = self._broker_service.get_broker_account_summary(
                company=company,
                account_type=Account.AccountType.LIVE)
            if live_broker_summary:
                company_snapshot.total_cash_holding = live_broker_summary.total_cash_value
                company_snapshot.excess_liquidity = live_broker_summary.excess_liquidity
                company_snapshot.total_maintenance_margin = live_broker_summary.full_maint_margin_req
                company_snapshot.total_asset_value = live_broker_summary.net_liquidation

        except Exception:
            logger.error("Error getting live summary in company snapshot, continuing")

        cash_positions, _ = self._hedge_position_service.get_cash_positions(company=company, date=self._ref_date)
        if last_snapshot:
            self._add_roll_cost_to_company_snap(company_snapshot=company_snapshot, cash_positions=cash_positions)

        # Get all the account snapshots that were created for this company.
        snapshots = SnapshotProvider().get_account_snapshots(company=company,
                                                             start_date=self._ref_date,
                                                             end_date=self._ref_date)

        # Sum abs fwd from all accounts' snapshots to get the total for the company.
        for snapshot in snapshots:
            if snapshot.account.is_live_account:
                company_snapshot.live_cashflow_abs_fwd += snapshot.cashflow_abs_fwd
                company_snapshot.num_live_cashflows_in_windows += snapshot.num_cashflows_in_window
            else:
                company_snapshot.demo_cashflow_abs_fwd += snapshot.cashflow_abs_fwd
                company_snapshot.num_demo_cashflows_in_windows += snapshot.num_cashflows_in_window

        # ==========================
        # Demo position summary
        # ==========================
        demo_positions = CompanyPositionsService.get_company_positions_summary(
            time=self._ref_date,
            company=company,
            positions_type=BrokerAccount.AccountType.PAPER,
            spot_fx_cache=universe)

        company_snapshot.demo_position_value = demo_positions.current_value
        company_snapshot.demo_unrealized_pnl = demo_positions.unrealized_pnl

        # ==========================
        # Live position summary
        # ==========================
        live_positions = CompanyPositionsService.get_company_positions_summary(
            time=self._ref_date,
            company=company,
            positions_type=BrokerAccount.AccountType.LIVE,
            spot_fx_cache=universe)

        company_snapshot.live_position_value = live_positions.current_value
        company_snapshot.live_unrealized_pnl = live_positions.unrealized_pnl

        # Save and return snapshot
        company_snapshot.save()
        return company_snapshot

    def _create_account_snapshots(self, company: Company):
        """
        Create all account snapshots for a company, as of the ref date of this service
        :param company: Company
        """
        accounts = Account.get_account_objs(company=company)
        for account in accounts:
            self.create_account_snapshot(account=account)

    def _cashflows_in_account_in_range(self, account: Account) -> bool:
        min_max_date = CashFlow.objects.filter(account=account).aggregate(min_date=Min('created'),
                                                                          max_date=Max('date'))
        min_date = min_max_date['min_date']
        max_date = min_max_date['max_date']
        if min_date and max_date:
            min_date = Date.to_date(min_max_date['min_date'])
            max_date = Date.to_date(min_max_date['max_date'])
            if min_date <= self._ref_date <= max_date:
                return True
        return False

    def generate_snapshot(self,
                          account: Account
                          ) -> Optional[AccountSnapshot]:
        """
        Create, but do not save, an account snapshot for a single account, as of the ref date of this service.

        :param account: Account, the account to create snapshot for
        """
        logger.debug(f"Generating snapshot for account {account} at time {self._ref_date}.")
        hedge_settings = HedgeSettings.get_hedge_settings(account)
        if not hedge_settings:
            logger.warning(f"Account {account} does not have hedge settings!")
        max_horizon = min(hedge_settings.max_horizon_days if hedge_settings else 365, 10 * 365 + 1)

        domestic = account.company.currency
        universe = self._get_universe(domestic=domestic)

        # Get realized PnL between last snapshot and now.
        last_snapshot: AccountSnapshot = self._snapshot_provider.get_last_account_snapshot(account=account,
                                                                                           date=self._ref_date)
        last_snapshot_date = Date.from_datetime(last_snapshot.snapshot_time) if last_snapshot else None
        logger.debug(f"Last snapshot date is {last_snapshot_date} for account {account}.")

        # Compute the day-over-day change in PnL and total PnL.
        if last_snapshot:
            change_in_realized_pnl = self._pnl_provider.get_realized_pnl(account=account,
                                                                         start_date=last_snapshot_date,
                                                                         end_date=self._ref_date,
                                                                         include_start_date=False,
                                                                         spot_fx_cache=universe)

            total_realized_pnl = change_in_realized_pnl.total_pnl + last_snapshot.total_realized_pnl
            logger.debug(f"Change in realized PnL: {change_in_realized_pnl}")
            logger.debug(f"Total realized PnL:     {total_realized_pnl}")
        else:
            logger.debug(f"There is no last snapshot for account {account}, setting realized PnL to 0.")
            change_in_realized_pnl, total_realized_pnl = PnLData(account.company.currency, 0.0, 0.0), 0.0

        # Calculate value of all positions.
        directional_positions_value, _ = self._hedge_position_service.get_total_value(account=account,
                                                                                      spot_fx_cache=universe,
                                                                                      date=self._ref_date,
                                                                                      ignore_domestic=True)
        logger.debug(f"Directional position value: {directional_positions_value}")

        # Compute Unrealized PnL
        unrealized_pnl = self._pnl_provider.get_unrealized_pnl(date=self._ref_date,
                                                               universe=universe,
                                                               account=account)

        total_unrealized_pnl = unrealized_pnl.total_pnl
        logger.debug(f"Total unrealized PnL: {unrealized_pnl}")
        if np.isnan(total_unrealized_pnl):
            logger.warning(f"While calculating account snapshot, unrealized PnL is NaN for account {account} on "
                           f"vd {self._ref_date}")

        # Create (but do not save) the snapshot.
        snapshot = AccountSnapshot(account=account,
                                   snapshot_time=self._ref_date,
                                   total_realized_pnl=total_realized_pnl,
                                   directional_positions_value=directional_positions_value)
        logger.debug(f"Created an account snapshot for account {account} at time {self._ref_date}.")
        snapshot.change_in_realized_pnl_fxspot = change_in_realized_pnl.fxspot_pnl
        snapshot.change_in_realized_pnl_fxforward = change_in_realized_pnl.fxforward_pnl
        logger.debug(f"Change in realized PnL, FxSpot:    {snapshot.change_in_realized_pnl_fxspot}")
        logger.debug(f"Change in realized PnL, FxForward: {snapshot.change_in_realized_pnl_fxforward}")

        snapshot.unrealized_pnl_fxspot = unrealized_pnl.fxspot_pnl
        snapshot.unrealized_pnl_fxforward = unrealized_pnl.fxforward_pnl
        logger.debug(f"Unrealized PnL, FxSpot:    {snapshot.unrealized_pnl_fxspot}")
        logger.debug(f"Unrealized PnL, FxForward: {snapshot.unrealized_pnl_fxforward}")

        cashflows, fx_pairs, _ = self._cashflow_pricer.get_flows_for_account(account=account,
                                                                             date=self._ref_date,
                                                                             max_horizon=max_horizon,
                                                                             inclusive=False,
                                                                             include_end=True)
        logger.debug(f"Got {len(cashflows)} cashflows for account {account}, max horizon was {max_horizon} days.")

        # Get fx/cash positions.
        cash_positions, position_objs = self._hedge_position_service.get_cash_positions(account=account,
                                                                                        date=self._ref_date)

        # Record how many cashflows there were.
        snapshot.num_cashflows_in_window = len(cashflows)

        # Get summary of cashflow value
        cash_val = self._cashflow_pricer.get_cashflow_value_summary(cashflows=cashflows,
                                                                    universe=universe,
                                                                    domestic=domestic)

        if last_snapshot:
            # TODO / NOTE: When we refactor cashflows, we will not need this, though we add some related things
            #   that tracks how many cashflows were changed during the next day.
            snapshot.cashflow_meddling_adjustment = self._compute_cashflow_meddling(
                last_date=Date.from_datetime(last_snapshot.snapshot_time),
                account=account,
                max_horizon=max_horizon,
                last_npv=last_snapshot.cashflow_npv)
            if snapshot.cashflow_meddling_adjustment != 0:
                logger.debug(f"A cashflow meddling was detected, adjustment is "
                            f"{snapshot.cashflow_meddling_adjustment}.")

        # Current Net Present Value
        snapshot.cashflow_npv = cash_val.npv
        # Current sum of absolute values of NPVs
        snapshot.cashflow_abs_npv = cash_val.npv_abs
        logger.debug(f"Current cashflow NPV:       {snapshot.cashflow_npv}")
        logger.debug(f"Current cashflow NPV (abs): {snapshot.cashflow_abs_npv}")

        # Calculate what the cost of covering all cashflows with forwards would be.
        snapshot.cashflow_fwd = cash_val.fwd
        # Sum of absolute values of forwards
        snapshot.cashflow_abs_fwd = cash_val.fwd_abs
        logger.debug(f"Current cashflow Fwd:       {snapshot.cashflow_fwd}")
        logger.debug(f"Current cashflow Fwd (abs): {snapshot.cashflow_abs_fwd}")

        # Get value of cashflows that rolled on into our time window since the last check.
        # This also calculates the cashflow meddling adjustment.
        self._add_cashflow_change_to_account_snap(snapshot=snapshot, last_snapshot=last_snapshot, universe=universe,
                                                  max_horizon=max_horizon, cash_val_summary=cash_val,
                                                  cash_positions=cash_positions)

        # Compute hedged and unhedged account values.
        total_pnl = total_realized_pnl + total_unrealized_pnl
        snapshot.hedged_value = snapshot.total_cashflow_roll_off + cash_val.npv + total_pnl \
                                + snapshot.cumulative_roll_value - snapshot.cumulative_commission
        snapshot.unhedged_value = snapshot.total_cashflow_roll_off + cash_val.npv
        logger.debug(f"Parts of hedged and unhedged value for account '{account}':")
        logger.debug(f"  * Cashflow rolloff: {snapshot.total_cashflow_roll_off}")
        logger.debug(f"  * Cashflow NPV:     {cash_val.npv}")
        logger.debug(f"  * Total PnL:        {total_pnl}")
        logger.debug(f"  * Cumulative roll:  {snapshot.cumulative_roll_value}")
        logger.debug(f"  * Cumulative comm:  {snapshot.cumulative_commission}")

        logger.debug(f"Hedged value:   {snapshot.hedged_value}")
        logger.debug(f"Unhedged value: {snapshot.unhedged_value}")

        if np.isnan(snapshot.hedged_value):
            logger.error(f"In account snapshot creation for account {account}: could not compute hedged value, "
                         f"value is NaN. Component values were:"
                         f"\n  * Total cashflow rolloff (+): {snapshot.total_cashflow_roll_off}"
                         f"\n  * Cashflow NPV (+):           {cash_val.npv}"
                         f"\n  * Total PnL (+):              {total_pnl} "
                         f"( = realized + unrealized, = {total_realized_pnl} + {total_unrealized_pnl})"
                         f"\n  * Cumulative roll value (+):  {snapshot.cumulative_roll_value}"
                         f"\n  * Cumulative commission (-):  {snapshot.cumulative_commission}"
                         )

        if np.isnan(snapshot.unhedged_value):
            logger.error(f"In account snapshot creation for account {account}: could not compute un-hedged value, "
                         f"value is NaN. Component values were:"
                         f"\n  * Total cashflow rolloff (+): {snapshot.total_cashflow_roll_off}"
                         f"\n  * Cashflow NPV (+):           {cash_val.npv}"
                         )

        logger.debug(f"From account snapshot creation (account {account}): hedged value is {snapshot.hedged_value}, "
                    f"and unhedged value is {snapshot.unhedged_value}.")

        # Make an approximation of the "theta" from Fx forwards.
        fxforward_theta = self._pnl_provider.get_approximate_forwards_theta(date=self._ref_date,
                                                                            universe=universe,
                                                                            account=account)
        snapshot.fxforward_theta_approximate = fxforward_theta
        logger.debug(f"Fx forward theta (approximate): {fxforward_theta}")

        # Add realized variance (since last snapshot)
        self._add_realized_var_to_account_snap(snapshot=snapshot, last_snapshot=last_snapshot,
                                               roll_on_correction=snapshot.cashflow_roll_on)

        # Compute any trading activity that happened during the day.
        self._add_trading_activity_to_account_snap(snapshot=snapshot, last_snapshot=last_snapshot)

        # Compute Margin (this is just an approximation at the account level of its contribution to margin)
        self._add_margin_estimate_to_account_snap(snapshot=snapshot, universe=universe, position_objs=position_objs)

        return snapshot

    def create_account_snapshot(self,
                                account: Account,
                                overwrite_next_in_last: bool = False,
                                do_save: bool = True,
                                ) -> Optional[AccountSnapshot]:
        if not self._cashflows_in_account_in_range(account=account):
            return
        logger.debug(f"Creating snapshot for account {account} at time {self._ref_date}.")
        snapshot = self.generate_snapshot(account=account)
        if snapshot is not None:
            # Save updates.
            if do_save:
                logger.debug(f"Saving snapshot for account {account} at time {self._ref_date}.")
                snapshot.save()

            if snapshot.last_snapshot is not None:
                last_snapshot = snapshot.last_snapshot
                if overwrite_next_in_last:
                    if last_snapshot.next_snapshot is not None:
                        logger.error(f"Last snapshot (id = {snapshot.last_snapshot}) already has a next snapshot "
                                     f"(id = {last_snapshot.next_snapshot}). Check this. "
                                     f"This snapshot is id = {snapshot.id}. Overwriting so that this snapshot is "
                                     f"the next snapshot in the last snapshot.")
                    # Set this as the next snapshot in the last snapshot, and (potentially) save.
                    last_snapshot.next_snapshot = snapshot
                    if do_save:
                        snapshot.last_snapshot.save()
        else:
            logger.warning(f"Snapshot for account {account} was None at time {self._ref_date}, not saving.")
        return snapshot

    def _get_universe(self, domestic: Currency):
        universe = self._universes.get(domestic, None)
        if not universe:
            logger.debug(f"Couldn't find universe for domestic ({domestic}) cache, "
                         f"will try requesting it from service")
            universe = self._universe_provider_service.make_cntr_currency_universe(domestic=domestic,
                                                                                   ref_date=self._ref_date,
                                                                                   create_vols=False,
                                                                                   create_corr=False,
                                                                                   bypass_errors=True)
        return universe

    def _get_last_universe(self, domestic: Currency, last_date: Date):
        universe = self._last_universes.get(domestic, None)
        if not universe:
            logger.debug(f"Couldn't find last universe for domestic ({domestic}) from cache, "
                         f"will try requesting it from service")
            universe = self._universe_provider_service.make_cntr_currency_universe(domestic=domestic,
                                                                                   ref_date=last_date,
                                                                                   create_vols=False,
                                                                                   create_corr=False,
                                                                                   bypass_errors=True)
        return universe

    @property
    def _spot_cache(self) -> SpotFxCache:
        """ Since universes are spot caches, just return any universe."""
        return next(iter(self._universes.values()))

    def _add_roll_cost_to_company_snap(self,
                                       company_snapshot: CompanySnapshot,
                                       cash_positions: CashPositions
                                       ):
        # TODO: actually get the broker for the company
        rates_cache = self._rates_caches.get_cache(broker="IBKR")
        roll_value = 0  # TODO: np.nan?

        if not rates_cache:
            logger.error(
                "Couldn't find the rates cache for broker, skipping roll cost calculation for company snapshot.")
        else:
            try:
                company = company_snapshot.company
                roll_value = self._roll_cost_calculator.get_roll_cost_for_cash_positions(
                    start_date=self._ref_date,
                    end_date=self._ref_date + 1,
                    dc=self._dc,
                    domestic=company.currency,
                    rates_cache=rates_cache, positions=cash_positions,
                    spot_fx_cache=self._spot_cache)
            except Exception as e:
                logger.error(f"Error computing roll cost for company snapshot: {e}")

        company_snapshot.daily_roll_value = roll_value

    def _add_realized_var_to_account_snap(self,
                                          snapshot: AccountSnapshot,
                                          last_snapshot: Optional[AccountSnapshot],
                                          roll_on_correction: float
                                          ):
        logger.debug(f"Adding realized var info to account snapshot, roll-on correction is {roll_on_correction}.")
        if not last_snapshot:
            logger.debug(f"No last snapshot, skipping.")
            return

        last_snapshot_date = Date.from_datetime(last_snapshot.snapshot_time)
        dt = self._dc.year_fraction(start=last_snapshot_date, end=self._ref_date)

        # To correct the diff, we have to take into account that today's unhedged value differs from yesterday not only
        # due to trading and market prices changing, but due to cashflows that rolled on (increasing today's account
        # value) and cashflows that rolled off (decreasing today's account value).
        # Hedged and unhedged values already incorporate all rolled off cashflows, so we only need ot
        if 0 < dt:
            correction = roll_on_correction + snapshot.meddling_adjustment_or_zero

            # Calculate cumulative_unhedged_variance
            diff_unhedged = snapshot.unhedged_value - last_snapshot.unhedged_value - correction

            # Calculate cumulative_hedged_variance.
            diff_hedged = snapshot.hedged_value - last_snapshot.hedged_value - correction

            snapshot.daily_hedged_modified_change = np.minimum(diff_hedged, np.maximum(0., diff_unhedged))
            snapshot.daily_hedged_earning = np.maximum(0., diff_hedged - snapshot.daily_hedged_modified_change)
            snapshot.daily_hedged_modified_variance = np.square(snapshot.daily_hedged_modified_change) / dt

            snapshot.daily_unhedged_variance = np.square(diff_unhedged) / dt
            snapshot.daily_hedged_variance = np.square(diff_hedged) / dt

            logger.debug(f"Difference info:")
            logger.debug(f"  * Diff hedged: {diff_hedged}")
            logger.debug(f"  * Diff unhedged: {diff_unhedged}")
            logger.debug(f"  * DT = {dt}")

            if 0 < snapshot.daily_unhedged_variance:
                snapshot.one_day_variance = snapshot.daily_hedged_variance / snapshot.daily_unhedged_variance
                logger.debug(f"One day variance: {snapshot.one_day_variance}")
            else:
                snapshot.one_day_variance = None

    def _add_cashflow_change_to_account_snap(self,
                                             snapshot: AccountSnapshot,
                                             last_snapshot: Optional[AccountSnapshot],
                                             universe: Universe,
                                             max_horizon: int,
                                             cash_val_summary: CashflowValueSummary,
                                             cash_positions: CashPositions):
        logger.debug(f"Adding cashflow change info to account snapshot, max horizon is {max_horizon}.")
        if last_snapshot is None:
            logger.debug(f"No last snapshot, skipping.")
            return

        account = snapshot.account
        last_snapshot_date = Date.from_datetime(last_snapshot.snapshot_time)

        # Set last snapshots. Do not modify last snapshot here, since this may just be a dummy creation of a snapshot.
        snapshot.last_snapshot = last_snapshot

        # Calculate value of cashflows that rolled off since the last snapshot.
        #
        # The hedge engine uses inclusive = False to get NPV, meaning it counts a cashflow as having
        # rolled off in the last day if it occurs exactly at that time. Therefore, cashflows that rolled off
        # in the last day are those that satisfy: last_time < pay_time <= date
        rolled_off, num_rolled_off = self._cashflow_pricer.get_historical_cashflows_value_for_account(
            start_date=last_snapshot_date,
            end_date=self._ref_date,
            account=account,
            inclusive=False,
            include_end=True)
        snapshot.cashflow_roll_off = rolled_off
        snapshot.total_cashflow_roll_off = rolled_off + last_snapshot.total_cashflow_roll_off
        snapshot.num_cashflows_rolled_off = num_rolled_off
        logger.debug(f"Cashflow info for range {last_snapshot_date} to {self._ref_date}:")
        logger.debug(f"  * Cashflow rolloff:         {rolled_off}")
        logger.debug(f"  * Num cashflows rolled off: {num_rolled_off}")
        logger.debug(f"  * Total cashflow roll off:  {snapshot.total_cashflow_roll_off}")

        # Calculate value of cashflows that rolled on since the last snapshot.
        last_max_date = last_snapshot_date + max_horizon
        max_date = self._ref_date + max_horizon
        rolled_on, rolled_on_abs, num_rolled_on = self._cashflow_pricer.get_npv_for_cashflows_in_range(
            date=self._ref_date,
            account=account,
            start_date=last_max_date + 1,
            end_date=max_date + 1,  # TODO: I adjusted these to make things work, but make sure everything is kosher.
            universe=universe,
            inclusive=True,
            include_end=True)
        snapshot.cashflow_roll_on = rolled_on
        snapshot.num_cashflows_rolled_on = num_rolled_on

        # Calculate change in NPV
        snapshot.change_in_npv = (cash_val_summary.npv
                                  + rolled_off - rolled_on
                                  - snapshot.cashflow_meddling_adjustment) \
                                 - last_snapshot.cashflow_npv
        logger.debug(f"Change in NPV: {snapshot.change_in_npv}")

        # Calculate the roll value from positions.
        try:
            rates_cache = self._rates_caches.get_cache(broker="IBKR")  # TODO: stop hard-coding... at some point.
            roll_value = self._roll_cost_calculator.get_roll_cost_for_cash_positions(
                start_date=last_snapshot_date,
                end_date=self._ref_date,
                spot_fx_cache=self._spot_cache,
                domestic=account.domestic_currency,
                rates_cache=rates_cache,
                positions=cash_positions,
                dc=self._dc)
            logger.debug(f"Roll value: {roll_value}")
        except Exception as e:
            roll_value = 0
            logger.error(f"Error calculating roll value for account: {account.get_name()}, {e}")

        snapshot.daily_roll_value = roll_value
        snapshot.cumulative_roll_value = last_snapshot.cumulative_roll_value + roll_value

    def _add_margin_estimate_to_account_snap(self,
                                             snapshot: AccountSnapshot,
                                             universe: Universe,
                                             position_objs: Sequence[FxPosition]):
        logger.debug(f"Adding margin estimation to snapshot.")
        try:
            account = snapshot.account
            spot_vols = universe.fx_universe.fx_vols
            margin_calc = MarginCalculator_UnivariateGaussian(spot_fx_cache=self._spot_cache, spot_vols=spot_vols)

            pairs = []
            values = []
            for position_obj in position_objs:
                pairs.append(position_obj.fxpair.name)
                values.append(position_obj.amount)
            fx_positions = pd.Series(data=values, index=pairs, dtype=float)
            margin = margin_calc.compute_margin_for_position(positions=fx_positions,
                                                             domestic=account.domestic_currency)
            logger.debug(f"Computed margin estimate: {margin}")
        except Exception as e:
            logger.error(f"Account Snapshot error computing margin estimate: {e}")
            margin = np.nan

        snapshot.margin = margin

    def _add_trading_activity_to_account_snap(self,
                                              snapshot: AccountSnapshot,
                                              last_snapshot: Optional[AccountSnapshot]):
        logger.debug(f"Adding trading activity to snapshot.")
        account = snapshot.account
        last_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(
            company=account.company, time=self._ref_date)

        requests = self._account_hedge_request_service.get_account_hedge_requests_for_account(
            account=account,
            company_hedge_action=last_hedge_action)

        last_total_commission = 0 if last_snapshot is None else last_snapshot.cumulative_commission
        total_traded, daily_commission = 0, 0
        for request in requests:
            quote_currency = request.quote_currency

            if request.commission is not None:
                if not np.isnan(request.commission):
                    daily_commission += self._spot_cache.convert_value(value=request.commission,
                                                                       from_currency=quote_currency,
                                                                       to_currency=account.domestic_currency)
                else:
                    logger.warning(f"Commission for account hedge requests {request.id} is NaN.")

            if request.price is not None:
                total_traded += self._spot_cache.convert_value(value=request.price[0],
                                                               from_currency=quote_currency,
                                                               to_currency=account.domestic_currency)
        snapshot.daily_commission = daily_commission
        snapshot.daily_trading = total_traded
        snapshot.cumulative_commission = daily_commission + last_total_commission
        logger.debug(f"Trading activity for account {account}:")
        logger.debug(f"  * Daily commission:      {daily_commission}")
        logger.debug(f"  * Daily trading:         {total_traded}")
        logger.debug(f"  * Cumulative commission: {snapshot.cumulative_commission}")

    def _compute_cashflow_meddling(self,
                                   last_date: Date,
                                   account: Account,
                                   max_horizon: int,
                                   last_npv: float):
        """
        Recompute the NPV from the last snapshot using the current view of the cashflows. If anything about the
        cashflows or hedge settings are now different in a way that matters, it will show up as a difference in the
        NPV of the cashflows.
        """
        # Get the cashflows, as of the last snapshot time.
        cashflows, fx_pairs, domestic = self._cashflow_pricer.get_flows_for_account(account=account,
                                                                                    date=last_date,
                                                                                    max_horizon=max_horizon,
                                                                                    inclusive=False,
                                                                                    include_end=True)

        last_universe = self._get_last_universe(last_date=last_date, domestic=domestic)

        # Recompute the NPV as of the last snapshot time.
        cash_val = self._cashflow_pricer.get_cashflow_value_summary(cashflows=cashflows,
                                                                    universe=last_universe,
                                                                    domestic=domestic)

        return cash_val.npv - last_npv
