from itertools import chain
from typing import Dict, Optional

from hdlib.Hedge.Fx.Util.LiquidityPool import LiquidityPool

from hdlib.Core.AccountInterface import AccountInterface
from hdlib.DateTime.Date import Date
from hdlib.Universe.Universe import Universe
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange

from main.apps.account.models import Account, Company
from main.apps.currency.models import FxPair
from main.apps.hedge.calculators.company_hedge import CompanyHedgeCallback
from main.apps.hedge.calculators.liquidity_adjust import get_liquidity_adjusted_positions
from main.apps.hedge.models import CompanyHedgeAction, AccountDesiredPositions
from main.apps.hedge.models.demo_orders import DemoOrders
from main.apps.hedge.models.liquidity_pool_record import LiquidityPoolRecord
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.oms import OMSHedgeService, OMSHedgeServiceInterface
from main.apps.ibkr.models import WireInstruction
from main.apps.margin.models import MarginDetail
from main.apps.margin.services.margin_service import MarginProviderService, DefaultMarginProviderService, \
    MarginProviderServiceInterface

import logging

from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.notification.utils.email import send_positions_liquidating_email

logger = logging.getLogger(__name__)


class StandardCompanyHedgeCallback(CompanyHedgeCallback):
    """
    The EOD service version of a Company Hedge Callback object that creates account hedge requests, submits orders
    to the OMS, and does accounting with the DB.
    """

    def __init__(self,
                 company_hedge_action: CompanyHedgeAction,
                 universe: Universe,
                 account_hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService(),
                 oms_hedge_service: OMSHedgeServiceInterface = OMSHedgeService(),
                 margin_provider_service: MarginProviderServiceInterface = DefaultMarginProviderService(),
                 ):
        self._company_hedge_action = company_hedge_action
        self._universe = universe
        self._account_hedge_request_service = account_hedge_request_service
        self._oms_hedge_service = oms_hedge_service
        self._margin_provider_service = margin_provider_service

    @property
    def company(self):
        return self._company_hedge_action.company

    def notify_account_position_changes(self,
                                        live_changes: Dict[AccountInterface, PositionChange],
                                        demo_changes: Dict[AccountInterface, PositionChange]):
        # Create the account hedge requests associated with this hedging.
        for account, position_change in chain(live_changes.items(), demo_changes.items()):
            logger.debug(f"Account {account}, change:")
            self._print_position_changes(position_change)

            status = self._account_hedge_request_service.create_account_hedge_requests(
                company_hedge_action=self._company_hedge_action,
                position_changes=position_change)
            # Log the status.
            if status.success():
                logger.debug(f"Creating account hedge requests for account {account} succeeded.")
            else:
                logger.warning(f"Creating account hedge requests for account {account} failed.")

            # Create desired account position records.
            AccountDesiredPositions.add_desired_positions(account=account,
                                                          positions=position_change.new_positions,
                                                          hedge_action=self._company_hedge_action)

    def notify_aggregated_changes(self, company: Company, agg_live_changes: PositionChange,
                                  agg_demo_changes: PositionChange):
        logger.debug(f"Company: {company}, LIVE change:")
        self._print_position_changes(agg_live_changes)
        logger.debug(f"Company: {company}, DEMO change:")
        self._print_position_changes(agg_demo_changes)
        logger.debug(f"Performing margin check for company {company} against LIVE positions")
        self._check_and_adjust_for_margin(company=company, positions=agg_live_changes)

        # Change PositionChanges to delta positions
        live_delta = agg_live_changes.delta_position()
        # Only need to submit orders if there are live positions.
        if 0 < len(live_delta):
            self._oms_hedge_service.submit_orders_for_company(company_hedge_action=self._company_hedge_action,
                                                              aggregated_changes=live_delta,
                                                              spot_fx_cache=self._universe)

        # Change PositionChanges to delta positions
        demo_delta = agg_demo_changes.delta_position()
        if 0 < len(demo_delta):
            fx_converter = FxMarketConventionService().make_fx_market_converter()
            DemoOrders.create_orders_from_delta(company_hedge_action=self._company_hedge_action,
                                                aggregated_changes=demo_delta,
                                                spot_fx_cache=self._universe,
                                                fx_converter=fx_converter)

    def apply_liquidity_changes(self,
                                live_account_exposures: Dict[FxPair, Dict[Account, float]],
                                demo_account_exposures: Dict[FxPair, Dict[Account, float]],
                                live_liquidity_changes: Dict[FxPair, float],
                                demo_liquidity_changes: Dict[FxPair, float],
                                ):
        """
        Adjust desired positions due to the fact that some liquidity is being absorbed by the liquidity pool.

        See get_liquidity_adjusted_positions for more information.
        """
        logger.debug(f"Applying liquidity changes.")

        live_desired_positions = AccountDesiredPositions.get_desired_positions_by_fx(
            hedge_action=self._company_hedge_action,
            live_only=True)
        live_position_adjustments = get_liquidity_adjusted_positions(account_exposures=live_account_exposures,
                                                                     desired_positions=live_desired_positions,
                                                                     liquidity_changes=live_liquidity_changes)
        # The live_positions_adjustments is covariant, but the type checker still complains, so I'm suppressing it.
        # noinspection PyTypeChecker
        AccountDesiredPositions.modify_positions_for_liquidity(liquidity_adjusted_amounts=live_position_adjustments,
                                                               is_live=True,
                                                               hedge_action=self._company_hedge_action)

        demo_desired_positions = AccountDesiredPositions.get_desired_positions_by_fx(
            hedge_action=self._company_hedge_action,
            live_only=False)
        demo_position_adjustments = get_liquidity_adjusted_positions(account_exposures=demo_account_exposures,
                                                                     desired_positions=demo_desired_positions,
                                                                     liquidity_changes=demo_liquidity_changes)
        # The live_positions_adjustments is covariant, but the type checker still complains, so I'm suppressing it.
        # noinspection PyTypeChecker
        AccountDesiredPositions.modify_positions_for_liquidity(liquidity_adjusted_amounts=demo_position_adjustments,
                                                               is_live=False,
                                                               hedge_action=self._company_hedge_action)

        # Add liquidity pool records.
        LiquidityPoolRecord.make_records(company_hedge_action=self._company_hedge_action,
                                         exposures=self._net_exposure(live_account_exposures),
                                         useage=live_liquidity_changes, is_live=True)
        LiquidityPoolRecord.make_records(company_hedge_action=self._company_hedge_action,
                                         exposures=self._net_exposure(demo_account_exposures),
                                         useage=demo_liquidity_changes, is_live=False)

    @staticmethod
    def _print_position_changes(change: PositionChange):
        for fx in sorted(change.old_positions.keys().union(change.new_positions.keys())):
            logger.debug(f"  * {fx}: {change.old_positions.get(fx, 0.)}  --->  {change.new_positions.get(fx, 0.)}")

    @staticmethod
    def _net_exposure(account_exposures: Dict[FxPair, Dict[Account, float]]):
        net_exposures = {}
        for fxpair, per_account in account_exposures.items():
            net = 0.
            for _, amount in per_account.items():
                net += amount
            net_exposures[fxpair] = net
        return net_exposures

    def _check_and_adjust_for_margin(self, company: Company, positions: PositionChange) -> Optional[MarginDetail]:
        logger.debug(f"Running margin check and adjustment.")
        baseline_margin = self._margin_provider_service.compute_margin_for_position(old_new_positions=positions,
                                                                                    company=company,
                                                                                    date=Date.today(),
                                                                                    account_type=Account.AccountType.LIVE)
        if baseline_margin is None:
            logger.debug(f"Baseline margin is None, this must be a test company or a backtest.")
            return None

        logger.debug(f" * Baseline margin: {baseline_margin}.")
        if baseline_margin.get_margin_health().is_unhealthy:

            logger.debug(f"Margin is unhealthy, starting position reduction.")
            try:
                send_positions_liquidating_email(broker_account=company.broker_accounts.first(), margin=baseline_margin,
                                                 wire_instruction=WireInstruction.objects.first())
            except Exception as ex:
                logger.error(f"Error sending positions liquidation email: {ex}")

            for ratio in [0.8, 0.6, 0.4, 0.2, 0.0]:
                logger.debug(f"Applying {ratio} reduction")
                positions.scale_new_positions(ratio)
                margin = self._margin_provider_service.compute_margin_for_position(old_new_positions=positions,
                                                                                   company=company,
                                                                                   date=Date.today(),
                                                                                   account_type=Account.AccountType.LIVE)
                if margin.get_margin_health().is_healthy:
                    logger.debug(f"  * Margin is healthy for company {company} with a reduction of {ratio}")
                    return margin
            logger.debug(f"  * Margin is still unhealthy for company {company} after all reductions")
            return baseline_margin
        logger.debug(f"  * Margin is healthy for company {company}")
        return baseline_margin
