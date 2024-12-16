from typing import List, Tuple, Any, Dict, Iterable, Optional

from hdlib.DateTime.Date import Date
from main.apps.account.models import Account, AccountTypes, Company
from main.apps.currency.models import FxPair
from main.apps.hedge.models import CompanyHedgeAction
from main.apps.hedge.models.account_hedge_request import AccountHedgeRequest
from main.apps.marketdata.services.fx.calendar import CalendarService
from main.apps.util import ActionStatus

from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange

# Logging.
import logging

logger = logging.getLogger(__name__)


class AccountHedgeRequestService(object):
    """
    Service responsible for creating and accessing Account hedge requests.
    """

    # ================================
    # Accessors.
    # ================================

    def get_account_hedge_requests(self,
                                   company_hedge_action: CompanyHedgeAction
                                   ) -> Dict[Account, List[AccountHedgeRequest]]:
        """
        Get a map of all the AccountHedgeRequests, by account, for a company hedge action.
        """
        requests = {}
        for request in AccountHedgeRequest.objects.filter(company_hedge_action=company_hedge_action):
            account = request.account
            if account not in requests:
                requests[account] = []
            requests[account].append(request)
        return requests

    @staticmethod
    def get_account_hedge_requests_in_range(company: Company,
                                            start_time: Optional[Date] = None,
                                            end_time: Optional[Date] = None,
                                            is_live: bool = True):
        filters = {"account__company": company,
                   "account__type": Account.AccountType.LIVE if is_live else Account.AccountType.DEMO}
        if start_time:
            filters["company_hedge_action__time__gte"] = start_time
        if end_time:
            filters["company_hedge_action__time__lt"] = end_time
        return AccountHedgeRequest.objects.filter(**filters)

    def get_account_hedge_requests_for_account(self,
                                               company_hedge_action: CompanyHedgeAction,
                                               account: AccountTypes
                                               ) -> Iterable[AccountHedgeRequest]:
        account_ = Account.get_account(account)
        if not account_:
            raise ValueError(f"cannot find the account {account}")
        return AccountHedgeRequest.objects.filter(company_hedge_action=company_hedge_action, account=account_)

    def are_all_requests_closed(self,
                                company_hedge_action: CompanyHedgeAction,
                                account_types: Tuple[Account.AccountType] = ()) -> bool:
        for request in AccountHedgeRequest.get_hedge_request_objs(company_hedge_action=company_hedge_action,
                                                                  account_types=account_types):
            if not request.is_closed:
                return False
        return True

    def get_account_hedge_requests_by_fxpair(self,
                                             company_hedge_action: CompanyHedgeAction,
                                             account_types: Tuple[Account.AccountType] = None,
                                             ) -> Dict[FxPairHDL, List[AccountHedgeRequest]]:
        """
        Get a map of all the AccountHedgeRequests, by account, for a company hedge action.
        """
        requests = {}
        for request in AccountHedgeRequest.get_hedge_request_objs(company_hedge_action=company_hedge_action,
                                                                  account_types=account_types):
            fx_pair = request.pair.to_FxPairHDL()
            if fx_pair not in requests:
                requests[fx_pair] = []
            requests[fx_pair].append(request)
        return requests

    def compute_changes(self,
                        position_changes: PositionChange) -> List[Tuple[Any, float]]:
        """
        Given a PositionChange object, compute the actual Fx position diffs.
        """
        old_set = set([x for x in position_changes.old_positions.index])
        new_set = set([x for x in position_changes.new_positions.index])
        all_fx_pairs = list(old_set.union(new_set))
        changes = []
        for fx_pair in all_fx_pairs:
            if fx_pair in new_set:
                if fx_pair in old_set:
                    amount = position_changes.new_positions[fx_pair] - position_changes.old_positions[fx_pair]
                else:
                    amount = position_changes.new_positions[fx_pair]
            else:
                amount = -position_changes.old_positions[fx_pair]
            # Add the change to the list. Include non-zero changes.
            changes.append((fx_pair, amount))
        return changes

    # ================================
    # Mutators.
    # ================================

    def create_account_hedge_requests(self,
                                      company_hedge_action: CompanyHedgeAction,
                                      position_changes: PositionChange
                                      ) -> ActionStatus:
        """
        Given the complete list of PositionChange objects, create all the AccountHedgeRequests. Note that the position
        change object is the pair of (old positions, new positions), not the actual change in positions.

        :returns: An action status.
        """
        changes = self.compute_changes(position_changes=position_changes)
        errors = []
        for pair, amount in changes:
            try:
                pair_ = FxPair.get_pair(pair)
                if pair_ is None:
                    errors.append(f"could not find pair {pair}")
                else:
                    # If the pair cannot be traded today, automatically close the hedge request.
                    status = AccountHedgeRequest.OrderStatus.OPEN
                    if not CalendarService().can_trade_or_trade_inverse_on_date(fx_pair=pair,
                                                                                date=company_hedge_action.time):
                        status = AccountHedgeRequest.OrderStatus.CLOSED

                    req = AccountHedgeRequest.objects.create(company_hedge_action=company_hedge_action,
                                                             account=position_changes.account,
                                                             pair=pair_,
                                                             requested_amount=amount,
                                                             status=status)

                    # If we could not actually make this trade, there is no PnL.
                    if req.status == AccountHedgeRequest.OrderStatus.CLOSED:
                        req.realized_pnl_domestic, req.realized_pnl_quote = 0.0, 0.0
                        req.commission, req.commission_cntr = 0.0, 0.0
                        req.avg_price, req.amount_filled = 0.0, 0.0

                        req.save()

            except Exception as ex:
                errors.append(f"Exception adding AccountHedgeRequest for {pair} (amount = {amount}): {ex}")
        if len(errors) == 0:
            return ActionStatus.log_and_success(f"Created {len(changes)} account hedge requests for account "
                                                f"{position_changes.account.get_name()}, associated with action "
                                                f"{company_hedge_action.id} (time {company_hedge_action.time}).")
        else:
            return ActionStatus.log_and_error(f"There were {len(errors)} errors in submitting "
                                              f"Account Hedge Requests: {errors}")
