import logging
from abc import abstractmethod, ABC
from copy import deepcopy
from typing import Optional, Dict, Tuple, List

import numpy as np
import pandas as pd
from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.CompanyInterface import CompanyInterface
from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.Hedge.Fx.CashPnLAccount import CashPnLAccountHistoryProvider
from hdlib.Hedge.Fx.HedgeAccount import CashExposures, HedgeAccountSettings, HedgeMethod
from hdlib.Hedge.Fx.HedgeCostProvider import HedgeCostProvider
from hdlib.Hedge.Fx.MinVar.MinVarPolicy import MinVarPolicy
from hdlib.Hedge.Fx.Policy import Policy, NoHedgeChangePolicy, PerfectHedgePolicy
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import FxMarketConverter
from hdlib.Hedge.Fx.Util.LiquidityPool import LiquidityPool
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from hdlib.Universe.Universe import Universe
from hdlib.Instrument.FxForward import FxForwardInstrument
from main.apps.currency.models import FxPair

logger = logging.getLogger(__name__)


def aggregate_changes(position_changes: List[PositionChange],
                      liquidity_pool: LiquidityPool) -> Tuple[pd.Series, PositionChange, Dict[FxPair, float]]:
    """
    Aggregate /net position changes across the desired changes in all accounts for a customer. In the process,
    exhaust any positions that can be met using the liquidity pool, to prevent trading when there are offsetting
    cash exposures available.

    :param position_changes: list of Position changes, one per account for a customer
    :param liquidity_pool: LiquidityPool, the liquidity pool to draw from instead of requesting an FxPosition
        whenever possible
    :return: a tuple, first element is the aggregated changes for the customer, the second element is the
        aggregated PositionChange object, the third is the amount of position absorbed by the liquidity pool.
    """
    # Aggregate total new and old FX positions.
    new_net_positions, old_net_positions = {}, {}
    for position in position_changes:
        for fxpair, amount in position.old_positions.items():
            old_net_positions[fxpair] = old_net_positions.get(fxpair, 0) + amount
        for fxpair, amount in position.new_positions.items():
            new_net_positions[fxpair] = new_net_positions.get(fxpair, 0) + amount

    # If there are no new positions, then there is nothing to "trade" against the liquidity pool.
    liquidity_changes = {}
    if 0 < len(new_net_positions):
        # Print the positions before we go to the liquidity pool.
        logger.debug(f"Before going to the liquidity pool, new net positions are:")
        for fx_pair, amount in new_net_positions.items():
            logger.debug(f"  * {fx_pair}: {amount}")
        original_new_net_positions = new_net_positions.copy()

        # Apply the liquidity pool to net positions, prevent us from trading if we have a natural hedge already
        # in place based on net exposures across all accounts
        # NOTE: these are always in market convention
        for fxpair, amount in new_net_positions.items():
            new_net_positions[fxpair] = liquidity_pool.get_residual_position(fx_pair=fxpair, desired_position=amount)
        # Print the positions after we go to the liquidity pool.
        logger.debug(f"After going to the liquidity pool, new net positions are:")

        for fx_pair, amount in new_net_positions.items():
            change = amount - original_new_net_positions.get(fx_pair)
            if 1.e-3 < abs(change):
                logger.debug(f"  * {fx_pair}: {amount} (change of {change})")
                liquidity_changes[fx_pair] = -change
            else:
                logger.debug(f"  * {fx_pair}: {amount}")

    # Then, compute the difference.
    difference = new_net_positions.copy()
    for fxpair, amount in old_net_positions.items():
        difference[fxpair] = difference.get(fxpair, 0) - amount

    old_net_positions = pd.Series(index=old_net_positions.keys(), data=old_net_positions.values(), dtype=float)
    new_net_positions = pd.Series(index=new_net_positions.keys(), data=new_net_positions.values(), dtype=float)

    if len(difference) == 0:
        index, changes = [], []
    else:
        index, changes = zip(*difference.items())
    return pd.Series(index=index, data=changes, dtype=float), \
           PositionChange(old_positions=old_net_positions,
                          new_positions=new_net_positions,
                          settings=None), \
           liquidity_changes


class CompanyHedgeCallback(ABC):
    @abstractmethod
    def notify_account_position_changes(self,
                                        live_changes: Dict[AccountInterface, PositionChange],
                                        demo_changes: Dict[AccountInterface, PositionChange]):
        raise NotImplementedError

    @abstractmethod
    def notify_aggregated_changes(self,
                                  company: CompanyInterface,
                                  agg_live_changes: PositionChange,
                                  agg_demo_changes: PositionChange,
                                  ):
        raise NotImplementedError

    @abstractmethod
    def apply_liquidity_changes(self,
                                live_account_exposures: Dict[FxPair, Dict[AccountInterface, float]],
                                demo_account_exposures: Dict[FxPair, Dict[AccountInterface, float]],
                                live_liquidity_changes: Dict[FxPair, float],
                                demo_liquidity_changes: Dict[FxPair, float],
                                ):
        raise NotImplementedError


class AccountPositionsProvider(ABC):
    @abstractmethod
    def get_fxspotpositions_for_account(self, account: AccountInterface) -> Dict[FxPairInterface, float]:
        raise NotImplementedError

    @abstractmethod
    def get_fxforwardpositions_for_account(self, account: AccountInterface) -> List[FxForwardInstrument]:
        raise NotImplementedError


class AccountPositionsProviderStored(AccountPositionsProvider):
    """
    An implementation of an AccountPositionsProvider that stores positions up front in a dictionary.
    """

    def __init__(self,
                 fxspot_positions: Dict[AccountInterface, Dict[FxPairInterface, float]],
                 fxforward_positions: Optional[Dict[AccountInterface, List[FxForwardInstrument]]] = None,
                 ):
        self._account_fxspot_positions = fxspot_positions
        self._account_fxforward_positions = fxforward_positions if fxforward_positions else {}

    def get_fxspotpositions_for_account(self, account: AccountInterface) -> List[FxForwardInstrument]:
        return self._account_fxspot_positions.get(account, {})

    def get_fxforwardpositions_for_account(self, account: AccountInterface) -> List[FxForwardInstrument]:
        return self._account_fxforward_positions.get(account, {})


class CompanyHedgeCalculator:
    def __init__(self,
                 company: CompanyInterface,
                 account_data: Dict[
                     HedgeAccountSettings, Tuple[CashExposures, CashExposures, CashPnLAccountHistoryProvider]],
                 universe: Universe,
                 cost_provider: HedgeCostProvider,
                 market_converter: FxMarketConverter,
                 callback: Optional[CompanyHedgeCallback] = None):
        self._company = company
        self._account_data = account_data
        self._universe = universe
        self._cost_provider = cost_provider
        self._market_converter = market_converter
        self._callback = callback

        # Aggregates the Fx exposures of all LIVE and DEMO accounts for the company.
        self._live_liquidity_pool = None
        self._demo_liquidity_pool = None

        # Make sure account data is correct.
        self._validate_accounts()

    @property
    def date(self):
        """ Get the date. """
        return self._universe.ref_date

    def hedge_company(self,
                      positions_provider: AccountPositionsProvider
                      ) -> Optional[Tuple[
        Tuple[pd.Series, PositionChange, Dict[FxPair, float]], Tuple[pd.Series, PositionChange, Dict[FxPair, float]]]]:

        logger.debug(f"Hedging company accounts on ref date {self.date}.")
        if len(self._account_data) == 0:
            empty_position_changes = (
                pd.Series(), PositionChange(old_positions=pd.Series(), new_positions=pd.Series()), {}
            )
            return empty_position_changes, empty_position_changes

        # Set up the liquidity pool.
        logger.debug(f"Initializing liquidity pool.")
        self._initialize_liquidity_pool()
        logger.debug(f"Done initializing liquidity pool.")

        # TODO: Allocate a fraction of the total margin to each account.
        margin_per_account = {}

        live_changes, demo_changes = {}, {}
        # Note: We assume all account are "active accounts."
        for settings, (cash_exposures, raw_cash_exposures, account_history_provider) in self._account_data.items():
            account = settings.get_account()
            margin_for_account = margin_per_account.get(account, np.inf)
            try:
                positions = self._get_hedge(settings=settings,
                                            raw_cash_exposures=raw_cash_exposures,
                                            cash_exposures=cash_exposures,
                                            account_history_provider=account_history_provider,
                                            margin=margin_for_account,
                                            positions_provider=positions_provider)
                # Store positions for live and demo account separately.
                if account.is_live_account:
                    live_changes[account] = positions
                else:
                    demo_changes[account] = positions
            except Exception as ex:
                # Even though we do not have to exit the function, this is still a major error, so we log it as such.
                logger.error(f"Error in getting hedge for account {account}: {ex}")

        # Pass the live and demo changes back up so, for example, account hedge requests can be created.
        if self._callback is not None:
            logger.debug(f"Calling notify_account_position_changes in the callback object.")
            try:
                self._callback.notify_account_position_changes(live_changes=live_changes, demo_changes=demo_changes)
            except Exception as ex:
                logger.debug(f"Callback function notify_account_position_changes failed: {ex}")
            logger.debug(f"Done calling notify_account_position_changes.")

        # Aggregate changes.

        demo_difference, demo_old_new_pos, demo_liquidity_changes = \
            aggregate_changes(list(demo_changes.values()), self._demo_liquidity_pool)
        live_difference, live_old_new_pos, live_liquidity_changes = \
            aggregate_changes(list(live_changes.values()), self._live_liquidity_pool)

        if self._callback is not None:
            logger.debug(f"Calling notify_aggregated_changes in the callback object.")
            try:
                self._callback.notify_aggregated_changes(company=self._company, agg_live_changes=live_old_new_pos,
                                                         agg_demo_changes=demo_old_new_pos)
            except Exception as ex:
                logger.error(f"Callback function notify_aggregated_changes failed: {ex}")

            if 0 < len(live_liquidity_changes) or 0 < len(demo_liquidity_changes):
                try:
                    self._callback.apply_liquidity_changes(
                        live_account_exposures=self._live_liquidity_pool.account_exposures,
                        demo_account_exposures=self._demo_liquidity_pool.account_exposures,
                        live_liquidity_changes=live_liquidity_changes,
                        demo_liquidity_changes=demo_liquidity_changes)
                except Exception as ex:
                    logger.error(f"Error in applying liquidity changes: {ex}")

            logger.debug(f"Done calling notify_aggregated_changes.")

        return (live_difference, live_old_new_pos, live_liquidity_changes), \
               (demo_difference, demo_old_new_pos, demo_liquidity_changes)

    def _get_hedge(self,
                   settings: HedgeAccountSettings,
                   raw_cash_exposures: CashExposures,
                   cash_exposures: CashExposures,
                   account_history_provider: CashPnLAccountHistoryProvider,
                   margin: float,
                   positions_provider: AccountPositionsProvider):
        """
        Get the hedge for a single account.
        """
        # Convert Market convention to counter-currency convention (ie, Foreign/Domestic for all pairs)
        positions_cntr, positions_mkt = self._get_fxspot_positions(settings=settings,
                                                                   positions_provider=positions_provider)

        # Initialize the Hedging Engine For account
        settings_cp = deepcopy(settings)
        settings_cp.margin_budget = min(settings.margin_budget, margin)  # Override margin settings
        policy = self._get_hedge_policy(settings=settings_cp)

        # Run the hedge (in counter currency convention)
        logger.debug(f"Calculating new hedge positions for account {settings.get_account()}.")
        summary = policy.new_positions(positions=positions_cntr,
                                       raw_exposures=raw_cash_exposures,
                                       cash_exposures=cash_exposures,
                                       universe=self._universe,
                                       cost_provider=self._cost_provider,
                                       account_history_provider=account_history_provider)
        new_positions_cntr = summary.positions

        # Convert the hedge into market convention
        new_positions_mkt = self._market_converter.convert_positions_to_market(fx_positions=new_positions_cntr,
                                                                               fx_cache=self._universe)
        logger.debug(f"Done calculating new hedge positions for account {settings.get_account()}. "
                    f"New positions: {'NONE' if len(new_positions_mkt) == 0 else ''}")
        for fx, amount in new_positions_mkt.items():
            logger.debug(f"  * {fx}: {amount}")

        # TODO: Doing this for now so we don't get type complaints, and just in case it really matters (it probably
        #  doesn't, we just use a series like a dictionary anyways). Get rid of all these series, and
        #  just use a Dict[FxPairInterface, float] everywhere instead.
        positions_mkt = pd.Series(index=positions_mkt.keys(), data=positions_mkt.values(), dtype=float)

        return PositionChange(settings=settings, old_positions=positions_mkt, new_positions=new_positions_mkt)

    def _get_fxspot_positions(self,
                              settings: HedgeAccountSettings,
                              positions_provider: AccountPositionsProvider):
        # Get the existing hedge position (in market convention)
        positions_mkt = positions_provider.get_fxspotpositions_for_account(account=settings.get_account())

        logger.debug(f"Last positions for account {settings.get_account()}: "
                    f"{'NONE' if len(positions_mkt) == 0 else ''}")
        for fx, amount in positions_mkt.items():
            logger.debug(f"  * {fx}: {amount}")

        # Convert Market convention to counter-currency convention (ie, Foreign/Domestic for all pairs).
        # Also return the market positions.
        return self._market_converter.convert_positions_to_cntr_currency(fx_positions_mkt=positions_mkt,
                                                                         fx_cache=self._universe,
                                                                         domestic=settings.domestic), positions_mkt

    @staticmethod
    def _get_hedge_policy(settings: HedgeAccountSettings) -> Policy:
        """
        Create a policy from the hedge account settings.
        """
        if settings.method == HedgeMethod.NO_HEDGE:
            return NoHedgeChangePolicy(settings=settings)

        if settings.method == HedgeMethod.PERFECT:
            return PerfectHedgePolicy(settings=settings)

        if settings.method == HedgeMethod.MIN_VAR:
            return MinVarPolicy(settings=settings)

    def _initialize_liquidity_pool(self):
        # Make sure we have fresh liquidity pools.
        self._live_liquidity_pool = LiquidityPool()
        self._demo_liquidity_pool = LiquidityPool()

        for settings, (cash_exposures, _, _) in self._account_data.items():
            # Compute the net cash exposures for this account, in market convention
            net_exposures_mkt = self._market_converter.convert_positions_to_market(
                fx_positions=cash_exposures.net_exposures(),
                fx_cache=self._universe)

            account = settings.get_account()
            if account.is_live_account:
                logger.debug(f"Adding to live liquidity pool:")
                for fxpair, amount in net_exposures_mkt.items():
                    logger.debug(f"  * {fxpair}: {amount}")
                self._live_liquidity_pool.add_to_pool(full_exposure_mkt=net_exposures_mkt, account=account)
            else:
                logger.debug(f"Adding to demo liquidity pool:")
                for fxpair, amount in net_exposures_mkt.items():
                    logger.debug(f"  * {fxpair}: {amount}")
                self._demo_liquidity_pool.add_to_pool(full_exposure_mkt=net_exposures_mkt, account=account)

        # Summarize liquidity pool.
        # TODO.

    def _validate_accounts(self):
        for settings, _ in self._account_data.items():
            account = settings.get_account()
            account_company = account.get_company()
            if account_company != self._company:
                raise ValueError(f"account {account} has company {account_company}, "
                                 f"needed to have company {self._company}")
