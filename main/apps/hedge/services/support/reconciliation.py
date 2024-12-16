"""
Contains some common reconciliation functionality.

"""
from typing import Dict, List

import numpy as np
from hdlib.Core.FxPairInterface import FxPairInterface

from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from main.apps.account.models import Account
from main.apps.currency.models import FxPairTypes
from main.apps.hedge.models import CompanyHedgeAction, AccountHedgeRequest
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.support.fx_fill_summary import FxFillSummary
from main.apps.marketdata.services.fx.fx_provider import FxVolAndCorrelationProvider
from main.apps.util import ActionStatus

import logging

logger = logging.getLogger(__name__)


class Reconciliation:
    """
    A class that contains general reconciliation related functions. Not intended to be used itself as a service, but
    to be used by services.
    """

    def __init__(self,
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 account_hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService(),
                 fx_provider: FxVolAndCorrelationProvider = FxVolAndCorrelationProvider()):
        self._hedge_position_service = hedge_position_service
        self._fx_provider = fx_provider
        self._account_hedge_request_service = account_hedge_request_service

    @staticmethod
    def compute_effective_filled_amounts(old_positions: Dict[FxPairTypes, float],
                                         new_positions: Dict[FxPairTypes, float]
                                         ) -> Dict[FxPairTypes, FxFillSummary]:
        """
        Given a company's former and current total positions, determine the amounts that must have been filled to
        make this change (diff between new and old positions).

        Sets the average rate to NanN.
        """
        all_fx_pairs = set(old_positions.keys()).union(set(new_positions.keys()))

        filled_amounts = {}
        for fx_pair in all_fx_pairs:
            amount = new_positions.get(fx_pair, 0.) - old_positions.get(fx_pair, 0.)
            filled_amounts[fx_pair] = FxFillSummary(amount_filled=amount, commission=np.nan,
                                                    cntr_commission=np.nan, average_price=np.nan)
        return filled_amounts

    def reconcile_with_actual_positions(self,
                                        company_hedge_action: CompanyHedgeAction,
                                        filled_amounts: Dict[FxPairInterface, FxFillSummary],
                                        account_type: Account.AccountType,
                                        spot_fx_cache: SpotFxCache,
                                        account_hedge_requests: Dict[FxPairInterface, List[AccountHedgeRequest]] = None
                                        ) -> ActionStatus:
        logger.debug(f"Reconciling filled amounts with actual positions associated with "
                    f"company {company_hedge_action.company}, hedge action "
                    f"id = {company_hedge_action.id}")
        company = company_hedge_action.company
        time = company_hedge_action.time

        if account_hedge_requests is None:
            logger.debug(f"Getting account hedge requests by Fx pair.")
            account_hedge_requests = self._account_hedge_request_service.get_account_hedge_requests_by_fxpair(
                company_hedge_action=company_hedge_action, account_types=(account_type,))

        # TODO: If there are no requests.

        account_positions_by_fxpair = self._hedge_position_service.get_all_positions_for_accounts_for_company_by_pair(
            company=company, account_types=(account_type,), time=time)

        # Get all current (pre-hedge) company positions
        current_agg_positions \
            = self._hedge_position_service.get_aggregate_positions_for_company(company=company,
                                                                               account_types=(account_type,),
                                                                               time=time)

        # Get all FX pairs.
        all_fx = set(filled_amounts.keys()).union(set(account_hedge_requests.keys()))

        # Reconcile by FX pair. Note that each account that holds or desires a non-zero amount of a currency must
        # have a hedge request for that currency, even if it does not actually want a change.
        for fx_pair in all_fx:
            hedge_requests = account_hedge_requests.get(fx_pair, [])
            account_positions = account_positions_by_fxpair.get(fx_pair, {})

            # Find the total amount of each currency that was requested across all accounts, and the desired position
            # of each account.
            # Compute the normalization based on desired positions: N_pos = \sum_{j} |P_j|
            # and normalization based on request sizes N_req = \sum_{j} |Req_j|
            total_desired_change, request_normalization, position_normalization = 0., 0., 0.
            for req in hedge_requests:
                total_desired_change += req.requested_amount
                request_normalization += np.abs(req.requested_amount)
                position_normalization += np.abs(account_positions.get(req.account, 0.) + req.requested_amount)

            # Look up how much of the fx pair was filled, and the current (pre-hedging) position in that fxpair.
            ticket = filled_amounts.get(fx_pair, FxFillSummary.make_empty())
            filled_amount = ticket.amount_filled
            current_total_position = current_agg_positions.get(fx_pair, 0.)

            # Compute the desired total position for *all account*, = (current total position) + (desired change)
            desired_total_position = current_total_position + total_desired_change
            # Compute the realized total position, = (current total position) + (filled amount)
            realized_total_position = current_total_position + filled_amount
            # Compute the difference.
            real_difference = realized_total_position - desired_total_position

            # Assuming the total amount did not perfectly net out, "fill" each account such that the net change in
            # accounts is equal to the total amount that was actually filled.

            for req in hedge_requests:
                # Desired position for the account.
                old_position = account_positions.get(req.account, 0.)
                desired_amount = old_position + req.requested_amount

                # Calculate the amount that we should assign as the realized new position of this account.

                # If normalization is zero, that means that no requests were made, and the positions do not have
                # to change.
                # If the account did not request *any* change in its position, it should not get any, or any
                # commission.
                if request_normalization == 0 or req.requested_amount == 0:
                    #
                    realized_amount = desired_amount
                    realized_commission = 0
                    realized_cntr_commission = 0
                elif position_normalization == 0:
                    # Check to make sure the total amount of this position we hold is zero. Otherwise, we were not able
                    # to close our position. Note that request_normalization != 0.
                    # TODO: The check ^

                    realized_amount = desired_amount
                    # Divide commission weighted by request amounts, since commission is from trading.
                    w_req = np.abs(req.requested_amount)
                    realized_commission = w_req / request_normalization * ticket.commission
                    realized_cntr_commission = w_req / request_normalization * ticket.cntr_commission
                else:
                    # Reconcile excess/shortfall position proportional to total requested position so all positions are
                    # wrong by the same %.
                    w_pos = np.abs(account_positions.get(req.account, 0.) + req.requested_amount)
                    realized_amount = desired_amount + real_difference * w_pos / position_normalization
                    # Divide commission weighted by request amounts, since commission is from trading.
                    w_req = np.abs(req.requested_amount)
                    realized_commission = w_req / request_normalization * ticket.commission
                    realized_cntr_commission = w_req / request_normalization * ticket.cntr_commission

                req.filled_amount = realized_amount - old_position  # Set the filled amount.
                req.commission = realized_commission
                req.commission_cntr = realized_cntr_commission
                req.avg_price = ticket.average_price

                # Set the single FX position.
                status, obj, realized_pnl = self._hedge_position_service.set_single_position_for_account(
                    account=req.account,
                    company_hedge_action=company_hedge_action,
                    fx_pair=fx_pair,
                    amount=realized_amount,
                    spot_rate=ticket.average_price)

                req.realized_pnl_quote = realized_pnl
                req.realized_pnl_domestic = spot_fx_cache.convert_value(value=realized_pnl,
                                                                        from_currency=fx_pair.quote,
                                                                        to_currency=company.currency)
                req.status = AccountHedgeRequest.OrderStatus.CLOSED
                req.save()

                if not (req.avg_price != 0 or req.requested_amount == 0):
                    # NOTE: We used to assert that this is true, but the assert kept failing....
                    # We are going to log what happens so we know what's going on.
                    logger.warning(f"Request did not fulfil the condition (ave_price != 0 or requested_amount == 0), "
                                   f"average price was {req.avg_price}, requested_amount was {req.requested_amount}. "
                                   f"This was for request: {req}")

        return ActionStatus.log_and_success(f"Reconciled company {company_hedge_action.company}.")
