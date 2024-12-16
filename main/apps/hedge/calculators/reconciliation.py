from typing import Dict, List, Tuple, Optional

import numpy as np
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from hdlib.Utils.PnLCalculator import PnLCalculator

from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.FxPairInterface import FxPairInterface
from main.apps.hedge.models import FxPositionInterface
from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeRequestInterface, AccountHedgeResultInterface
from main.apps.hedge.support.fx_fill_summary import FxFillSummary
from main.apps.hedge.support.fxposition_interface import BasicFxPosition
from main.apps.hedge.support.reconciliation_data import ReconciliationData

import logging

logger = logging.getLogger(__name__)


def accumulate_keys(dictionaries: List[dict]) -> set:
    """ Get a set of all the keys in all the dictionaries in the input list. """
    keys = set({})
    for dictionary in dictionaries:
        for key in dictionary.keys():
            keys.add(key)
    return keys


class ReconciliationCalculator:
    def __init__(self):
        pass

    def reconcile_company(
        self,
        company_positions_before: Dict[FxPairInterface, float],
        company_positions_after: Dict[FxPairInterface, float],
        account_desired_positions: Dict[FxPairInterface, Dict[AccountInterface, float]],
        spot_cache: Optional[SpotFxCache],
        initial_account_positions: Dict[FxPairInterface, Dict[AccountInterface, FxPositionInterface]] = None,
        account_hedge_requests: Dict[FxPairInterface, List[AccountHedgeRequestInterface]] = None,
        filled_amounts: Dict[FxPairInterface, FxFillSummary] = None,
    ) -> Tuple[
        Dict[FxPairInterface, Dict[AccountInterface, FxPositionInterface]],
        List[ReconciliationData],
        List[AccountHedgeResultInterface]
    ]:
        if initial_account_positions is None:
            initial_account_positions = {}
        if account_hedge_requests is None:
            account_hedge_requests = {}
        if filled_amounts is None:
            filled_amounts = {}

        # Get any Fx pair that was a position or a request or a fill, or anything else.
        fx_pairs = accumulate_keys(dictionaries=[company_positions_before, company_positions_after,
                                                 initial_account_positions, account_hedge_requests,
                                                 account_desired_positions])

        # This will be the output data, that we fill during reconciliation.
        final_positions_by_fxpair: Dict[FxPairInterface, Dict[AccountInterface, FxPositionInterface]] = {}
        reconciliation_data, account_hedge_results = [], []

        logger.debug(f"Beginning per-pair reconciliation, there are {len(fx_pairs)} pairs to handle.")
        for it, fx_pair in enumerate(fx_pairs):
            logger.debug(f"Handling reconciliation for Fx pair {fx_pair} ({it + 1} / {len(fx_pairs)}).")

            # Reconciliation data tracks statistics about the company and account positions, requests, and trading.
            # We save these to the DB for later audit.
            data = ReconciliationData(fx_pair=fx_pair)
            data.initial_amount = company_positions_before.get(fx_pair, 0.0)
            data.final_amount = company_positions_after.get(fx_pair, 0.0)
            # Get the summary of the OMS fill for this Fx pair, or None if there was no fill.
            data.fill_summary = filled_amounts.get(fx_pair, None)

            # Calculate the total desired position and absolute sum of desired positions.
            for _, desired_position in account_desired_positions.get(fx_pair, {}).items():
                data.desired_final_amount += desired_position
                data.absolute_sum_of_desired_account_positions += np.abs(desired_position)
            logger.debug(f"For Fx pair {fx_pair}, total desired position is {data.desired_final_amount} "
                        f"and absolute sum of account desired positions is "
                        f"{data.absolute_sum_of_desired_account_positions}")

            logger.debug(f"  * Company initially had {data.initial_amount} of {fx_pair}, final amount was "
                        f"{data.final_amount}, difference is {data.change_in_position}. "
                        f"Amount ordered was {data.filled_amount}.")

            # Pull out the account positions and hedge requests for this specific Fx pair.
            account_positions = initial_account_positions.get(fx_pair, {})
            requests = account_hedge_requests.get(fx_pair, [])

            # CASE: There were no requested changes for the Fx pair.
            if len(requests) == 0:
                # There really shouldn't have been any trading if there were no account requests for trading - but
                # we will check to be sure.
                if data.filled_amount != 0:
                    logger.error(f"  * There were no AccountHedgeRequests provided to the ReconciliationCalculator "
                                 f"for Fx pair {fx_pair}, but there were summaries of trading occurring. "
                                 f"This is potentially a BUG.")

            # Calculate the total amount requested and some normalizations.
            #
            # Excess in positions are distributed based on the absolute size of the desired position, with the rational
            # that a larger position (in either direction) is effected less by a larger excess or shortfall.
            #
            # Trading costs are distributed according account request size, since an account that did not request any
            # trading should not incur trading costs.
            #
            # This is not the only way to do this, e.g. perhaps trading costs should be assigned the same way as
            # position changes, since if your position changed, there is a cost associated with that.
            requests_by_account = {}
            for request in requests:
                account = request.account
                requests_by_account[account] = request

                requested_amount = request.get_requested_amount()
                data.total_account_requested_change += requested_amount
                data.absolute_sum_of_account_requests += np.abs(requested_amount)

            # Fill up the final positions for this Fx pair, by account.
            final_account_positions = {}

            # Edge case: The total amount desired is zero, but the actual total position is non-zero. Hopefully, we
            # will always be able to close out a position, so this will only happen if that assumption is not correct,
            # or if there is a bug upstream, e.g. in getting all the tickets or account requests.
            if data.absolute_sum_of_desired_account_positions == 0 and data.final_amount != 0:
                logger.error(f"  * All account wanted zero position in Fx pair {fx_pair}, but the company has a "
                             f"balance of {data.final_amount} units of {fx_pair}.")

                # Check if any accounts held a position in this Fx pair yesterday. I imagine that under almost all
                # circumstance, this will be the case.
                last_positions_for_pair = initial_account_positions.get(fx_pair, None)

                # If some accounts held this fx pair, make them keep holding it. It could be, for example, that a user
                # deleted a cashflow for an account, causing the account (and all accounts) to sudden not want a
                # particular Fx pair. If this happens on a non-trading day, this will lead to all accounts not wanting
                # a position, but some of this Fx pair being held. (Obviously, we did actually encounter this case
                # in the wild.)
                if last_positions_for_pair:
                    total_last_position = 0.
                    abs_sum_position = 0.
                    account_positions, abs_last_account_positions = {}, {}

                    for account, position in last_positions_for_pair.items():
                        total_last_position += position.get_amount()
                        abs_sum_position += np.abs(position.get_amount())
                        abs_last_account_positions[account] = np.abs(position.get_amount())
                        account_positions[account] = position.get_amount()

                    # Case I: The total (net) position was zero or basically zero yesterday. In this case, we cannot
                    # use our preferred logic (see case II), since we cannot normalize by yesterday's net position.
                    # In this case, all accounts (that had positions yesterday) will divide up the remaining positions,
                    # taking a piece proportional to the absolute value of the size of the position they last held in
                    # this Fx pair.
                    if np.abs(total_last_position) < 1:
                        # Calculate "gamma" factor.
                        for account in account_positions.keys():
                            fraction = abs_last_account_positions[account] / abs_sum_position
                            account_positions[account] = data.final_amount * fraction

                    # Case II: The total position was non-zero and (potentially) increased or decreased some.
                    #
                    # The logic here is to let each account close (be selling if its position had been long, or buying
                    # if its position had been short) some fraction, gamma, of its account such that all accounts that
                    # held any amount of the position yesterday now collectively hold the amount of the Fx pair that
                    # exists today.
                    #
                    # Note: This really makes the most sense if the sign of the amount of the Fx pair that the company
                    # holds does not change sign. It is not clear what the best behavior is if the holding does change
                    # sign, but nothing terrible happens, so for now, I am covering that case with this logic as well.
                    else:
                        # Calculate "gamma" factor.
                        gamma = 1.0 - (data.final_amount / total_last_position)
                        for account in account_positions.keys():
                            position = account_positions[account]
                            account_positions[account] = position * (1.0 - gamma)

                    for account, amount in account_positions.items():
                        final_position = BasicFxPosition(account=account,
                                                         amount=amount,
                                                         fxpair=fx_pair,
                                                         # TODO: It's hard to know what to do here. This is just filler
                                                         #  code, so its probably not that important. We would probably
                                                         #  need to go back to yesterday's positions.
                                                         total_price=0.0)

                        final_account_positions[account] = final_position

                # If, magically, no account used to hold some Fx pair, but now the company *does* hold the Fx pair,
                # then all we can really do is just assign it in some way across accounts. This I *really* hope doesn't
                # ever occur, it could I suppose if people start trading in an account through IB.
                # For now, I am just going to split the positions evenly between all accounts that had positions last
                # time, or desire positions now.
                else:
                    all_accounts = set({})
                    for _, mp in account_desired_positions.items():
                        for account, _ in mp.items():
                            all_accounts.add(account)
                    for _, mp in initial_account_positions.items():
                        for account, _ in mp.items():
                            all_accounts.add(account)

                    for account in all_accounts:
                        final_position = BasicFxPosition(account=account,
                                                         amount=data.final_amount / len(all_accounts),
                                                         fxpair=fx_pair,
                                                         # TODO: It's hard to know what to do here. This is just filler
                                                         #  code, so its probably not that important. We would probably
                                                         #  need to go back to yesterday's positions.
                                                         total_price=0.0)

                        final_account_positions[account] = final_position
            else:
                # Distribute excess or shortfall back to the accounts. Set the filled amount in account hedge requests.

                excess = data.excess_amount
                desired_position = account_desired_positions.get(fx_pair, {})
                for account, amount in desired_position.items():
                    logger.debug(f"    ===== Reconciling for account {account} =====")
                    request = requests_by_account.get(account, None)

                    # If absolute_sum_of_desired_account_positions == 0, we can set the weight to (1 / num-account)
                    w_pos = np.abs(amount) / data.absolute_sum_of_desired_account_positions \
                        if 0 < data.absolute_sum_of_desired_account_positions else 1.0 / len(desired_position)

                    final_amount = amount + excess * w_pos

                    # The filled amount is the final amount minus the initial amount for the account.
                    initial_amount = 0.
                    fxposition = account_positions.get(account, None)
                    if fxposition:
                        initial_amount = fxposition.get_amount()
                    filled_amount = final_amount - initial_amount
                    # Don't count tiny numbers.
                    if np.abs(filled_amount) < 1.e-6:
                        filled_amount = 0.
                    data.filled_amount = filled_amount

                    logger.debug(f"    * Setting filled amount: {filled_amount} "
                                f"(final pos = {final_amount}, initial amount = {initial_amount})")

                    # Compute and set PnLs. Avg price will come from trade price, if a trade occurred, otherwise from
                    # the spot cache.
                    avg_price = self._get_avg_price(fx_pair=fx_pair, data=data, spot_cache=spot_cache)
                    if avg_price is None:
                        logger.error(f"    Trading occurred (filled amount was {data.filled_amount}) but avg "
                                     f"price was None (missing).")

                    # Calculate the new total price.
                    initial_position = account_positions.get(account, None)
                    initial_total_price = initial_position.get_total_price() if initial_position else 0.0

                    # If the position size changed, either due to trading in the market, or to liquidity pool trading.
                    if data.filled_amount != 0:
                        pnl_quote = self.calculate_pnl(fxposition=fxposition,
                                                       avg_price=avg_price,
                                                       final_amount=final_amount)

                        domestic = account.get_company().get_company_currency()
                        if domestic:
                            pnl_domestic = spot_cache.convert_value(value=pnl_quote,
                                                                    from_currency=fx_pair.get_quote_currency(),
                                                                    to_currency=domestic)

                            logger.debug(f"    * Setting PnL domestic = {pnl_domestic} "
                                        f"(company domestic is {domestic})")
                        else:
                            pnl_domestic = None
                            logger.warning(f"Cannot get company's currency, cannot fill in domestic PnL.")
                    else:
                        # No change in position, so no opportunity for PnL.
                        pnl_domestic = 0.
                        pnl_quote = 0.

                    # NOTE(Nate): It is irritating that we always store "total price" in absolute value terms.
                    # Whenever we need to work with it, we have to determine the actual sign of the total price,
                    # then do whatever arithmetic we need to do, then take the absolute value. It is easier to
                    # take the absolute value of a signed number than to always be re-signing quantities for every
                    # operation.
                    new_total_price = ReconciliationCalculator.calculate_total_price(
                        old_total_price=initial_total_price,
                        old_amount=initial_amount,
                        latest_avg_price=avg_price,
                        filled_amount=filled_amount)
                    logger.debug(f"    * Total price was {initial_total_price}, updating to {new_total_price}")

                    if request:
                        logger.debug(f"    * Setting information back in the account hedge request.")
                        # If there was a request, set the data in the corresponding result.
                        result = request.create_result_object()

                        result.set_filled_amount(filled_amount)
                        result.set_realized_pnl_quote(pnl_quote)
                        result.set_realized_pnl_domestic(pnl_domestic)
                        result.set_avg_price(avg_price)

                        # Distribute any commission.
                        if 0 < data.absolute_sum_of_account_requests:
                            w_com = np.abs(request.get_requested_amount()) / data.absolute_sum_of_account_requests
                        else:
                            w_com = 0.
                        commission, commission_cntr = w_com * data.commission, w_com * data.cntr_commission
                        result.set_commissions(commission=commission, cntr_commission=commission_cntr)
                        logger.debug(f"    * Setting commission = {commission}, cntr commission = {commission_cntr}")

                        account_hedge_results.append(result)
                    else:
                        logger.debug(f"    * No account hedge request, final position is {final_amount}.")

                    # Create output (final) FxPosition for this account and pair.
                    final_position = BasicFxPosition(account=account, amount=final_amount,
                                                     fxpair=fx_pair, total_price=new_total_price)
                    logger.debug(f"    >> Creating position for account {account}, {fx_pair}: Amount = {final_amount}, "
                                f"Price = {new_total_price}")

                    final_account_positions[account] = final_position

                    # Format a close to the reconciliation log for this account-fxpair.
                    logger.debug(f"    ==============================================================")

            # Set the outputs.
            final_positions_by_fxpair[fx_pair] = final_account_positions
            reconciliation_data.append(data)

            # If there is unexplained Fx, log that.
            # TODO(Nate): Figure out what to do about position total price. We've seen that if the position is closed
            #   e.g. by Jay just closing it, the position can be 0, but the price is still some large number. We will
            #   long term need a way for people to mark that the made manual trades on IB and mark PnL.
            if data.unexplained_change != 0:
                logger.warning(
                    f">> There was an unexplained change in {data.fx_pair}: {data.unexplained_change}")

        return final_positions_by_fxpair, reconciliation_data, account_hedge_results

    @staticmethod
    def _get_avg_price(fx_pair, data, spot_cache) -> float:
        # Compute and set PnLs.
        avg_price = data.average_price_from_trade

        # The avg price comes from trade tickets. If no trading occurred, but a change in position
        # did occur (for example, some FX reduction in one account was compensated by a gain in
        # another account), we won't have the avg price from a trading ticket, because no trading
        # will occur. In this case, we take a reference price from the spot cache, for bookkeeping
        # purposes.
        if avg_price is None:
            if spot_cache is not None:
                avg_price = spot_cache.get_fx(fx_pair=fx_pair)
                logger.warning(f"    Average price for {fx_pair} was None (generally means no "
                             f"trading occurred), fetching reference trade price from cache: "
                             f"{avg_price}.")
            else:
                logger.error(f"    Average price for {fx_pair} was None (generally means no "
                             f"trading occurred), and the spot cache was None. Cannot set a "
                             f"reference trade price.")
        return avg_price

    @staticmethod
    def calculate_pnl(fxposition: FxPositionInterface,
                      avg_price: float,
                      final_amount: float) -> float:
        old_amount = fxposition.get_amount() if fxposition else 0.0
        old_price_avg = fxposition.get_average_price() if fxposition else 0.0
        return PnLCalculator.calc_realized_pnl(old_amount=old_amount,
                                               new_amount=final_amount,
                                               old_price_avg=old_price_avg,
                                               new_price_avg=avg_price)

    @staticmethod
    def calculate_total_price(old_total_price: float,
                              old_amount: float,
                              latest_avg_price: float,
                              filled_amount: float):
        """
        Calculate the new total price of a position given the old total price of the position and the amount of change
        and average price of change.
        """
        if latest_avg_price is None:
            logger.error(f"In calculate total price, average price is None. Setting to zero, "
                         f"but find out what happened.")
            latest_avg_price = 0.0
        return np.abs(np.sign(old_amount) * old_total_price + latest_avg_price * filled_amount)
