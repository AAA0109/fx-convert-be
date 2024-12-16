from abc import ABCMeta, abstractmethod
from typing import Dict, Optional, Tuple, Set

import numpy as np
import pandas as pd

from hdlib.Core.FxPairInterface import FxPairInterface
from main.apps.currency.models.fxpair import FxPair
from main.apps.account.models import CompanyTypes, Account
from main.apps.broker.models import BrokerAccount
from main.apps.hedge.models import AccountHedgeRequest
from main.apps.hedge.models.company_hedge_action import CompanyHedgeAction
from main.apps.hedge.models.oms_order_request import OMSOrderRequest
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.support.reconciliation import Reconciliation
from main.apps.marketdata.services.fx.calendar import CalendarService
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.oems.services.order_service import OrderService, BacktestOrderService, OrderServiceInterface
from main.apps.oems.support.tickets import OMSOrderTicket
from main.apps.util import ActionStatus

from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)

PROTOCOL = 'https'
if PROTOCOL == 'https':
    import urllib3

    urllib3.disable_warnings()


class OMSHedgeServiceInterface(metaclass=ABCMeta):
    @abstractmethod
    def submit_orders_for_company(self, company_hedge_action: CompanyHedgeAction,
                                  aggregated_changes: pd.Series,
                                  spot_fx_cache: Optional[SpotFxCache] = None):
        """
        Given the aggregated changes in positions for a company, aggregated from all the hedging activity required for
        all the company's accounts, create all the DB records necessary for trading and submitting the actual orders
        to the OMS API.

        :param company_hedge_action: CompanyHedgeAction, The company hedge action associated with these changes and
            that all orders should reference.
        :param aggregated_changes: pd.Series, The aggregated changes that need to be made to the company's account.
            The FX pairs must be market convention fx pairs.
        :param spot_fx_cache: Optional[SpotFxCache], if provided, this will be used to set expected costs, so we can
            later compare actual costs to expected costs.
        """
        pass

    @abstractmethod
    def cancel_all_orders_for_company(self, company: CompanyTypes) -> ActionStatus:
        pass

    @abstractmethod
    def has_open_orders(self, company: CompanyTypes) -> bool:
        """ Check if a company has any open orders """
        pass

    @abstractmethod
    def has_unreconciled_orders_for_action(self,
                                           company_hedge_action: CompanyHedgeAction,
                                           account_type: Account.AccountType) -> bool:
        """ Check if a company has any open orders """
        pass

    @abstractmethod
    def submit_order(self,
                     request: OMSOrderRequest) -> ActionStatus:
        """
        Submit an order to the OMS.
        """
        pass

    @abstractmethod
    def reconcile_company_orders_for_account_type(self,
                                                  account_type: Account.AccountType,
                                                  company_hedge_action: CompanyHedgeAction,
                                                  spot_fx_cache: SpotFxCache) -> ActionStatus:
        """
        Do the order reconciliation for a company, determining how to allocate purchased FX back to the individual
        accounts.
        """
        pass

    @abstractmethod
    def reconcile_company_orders(self,
                                 company_hedge_action: CompanyHedgeAction,
                                 spot_fx_cache: SpotFxCache,
                                 ) -> Tuple[ActionStatus, Set[Account.AccountType]]:
        """
        Reconcile company orders for each account type (e.g. live, demo).
        """
        pass

    @abstractmethod
    def are_tickets_from_hedge_complete(self,
                                        company_hedge_action: CompanyHedgeAction,
                                        account_type: Account.AccountType) -> bool:
        pass

    @abstractmethod
    def get_filled_amount_per_fx_pair_for_company(self,
                                                  company_hedge_action: CompanyHedgeAction,
                                                  account_type: Account.AccountType,
                                                  spot_cache: SpotFxCache,
                                                  ) -> Optional[Dict[FxPair, OMSOrderTicket]]:
        pass


class OMSHedgeService(OMSHedgeServiceInterface):
    """
    Service responsible for submitting orders to the OMS and for reconciling trades with the accounts.
    """

    def __init__(self,
                 reconcilation: Reconciliation = Reconciliation(),
                 account_hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService(),
                 calendar_service: CalendarService = CalendarService(),
                 convention_service: FxMarketConventionService = FxMarketConventionService(),
                 order_service: OrderServiceInterface = OrderService()):
        self._reconciliation = reconcilation
        self._account_hedge_request_service = account_hedge_request_service
        self._calendar_service = calendar_service
        self._convention_service = convention_service
        self._order_service = order_service

    # All types of hedgable accounts.
    hedgeable_account_types = (Account.AccountType.LIVE, Account.AccountType.DEMO)

    def submit_orders_for_company(self,
                                  company_hedge_action: CompanyHedgeAction,
                                  aggregated_changes: pd.Series,
                                  spot_fx_cache: Optional[SpotFxCache] = None):
        """
        Given the aggregated changes in positions for a company, aggregated from all the hedging activity required for
        all the company's accounts, create all the DB records necessary for trading and submitting the actual orders
        to the OMS API.

        :param company_hedge_action: CompanyHedgeAction, The company hedge action associated with these changes and
            that all orders should reference.
        :param aggregated_changes: pd.Series, The aggregated changes that need to be made to the company's account.
            The FX pairs must be market convention fx pairs.
        :param spot_fx_cache: Optional[SpotFxCache], if provided, this will be used to set expected costs, so we can
            later compare actual costs to expected costs.
        """
        # TODO: ensure that the hedge will stay healthy!!!! Call the MarginProviderService "what-if" method

        time = company_hedge_action.time
        company = company_hedge_action.company
        logger.debug(f"Submitting {len(aggregated_changes)} OMS orders for action {company_hedge_action.id}, "
                    f"action time {time}")

        # Get the broker account for the company. NOTE: There should only be one broker account.
        all_broker_account = BrokerAccount.get_accounts_for_company(company=company)
        if all_broker_account is None or len(all_broker_account) == 0:
            raise ValueError(f"cannot submit orders for company to the OMS, there is no broker account associated"
                             f"with company {company}")
        broker_account = all_broker_account[0]

        # Create CompanyHedgeRequest objects from the aggregated_changes. Convert order changes into changes that are
        # in terms of actually traded pairs. Aggregate these orders.
        num_fx_orders = 0
        for fx_pair, unrounded_change in aggregated_changes.items():
            # Make sure amount is valid.
            if np.isnan(unrounded_change):
                logger.error(f"Un-rounded change for {fx_pair} is NaN, not creating order.")
                continue
            if np.isinf(unrounded_change):
                logger.error(f"Un-rounded change for {fx_pair} is Inf, not creating order.")
                continue

            # Create the CompanyHedgeRequest record.
            fx_pair: FxPairHDL  # To supress warnings.
            market_converter = self._convention_service.make_fx_market_converter()
            if self._calendar_service.can_trade_fx_on_date(fx_pair=fx_pair, date=time):
                # Change irregular lot sizes into regular lot sizes.
                # Right now, we just round lots towards zero, but there is a case to be made to just rounding, or doing
                # something else more complex.
                rounded_change = market_converter.round_to_lot(fx_pair=fx_pair, amount=unrounded_change)
                logger.debug(f"Can trade on date {time}, creating OMS hedge request. Rounding order of "
                            f"{unrounded_change} to {rounded_change}.")

                # Estimate how much the trade will cost.
                expected_cost = None
                if spot_fx_cache:
                    rate = spot_fx_cache.get_fx(fx_pair=fx_pair)
                    if rate:
                        expected_cost = rounded_change * rate
                        logger.debug(f"Setting expected cost for {rounded_change} of {fx_pair} to be {expected_cost}.")
                else:
                    logger.debug(f"Could not calculated expected cost of order.")

                # Create an OMSOrderRequest entry, and submit the order to the OMS.
                status, order_request = OMSOrderRequest.add_oms_order_request(
                    company_hedge_action=company_hedge_action,
                    fx_pair=fx_pair,
                    unrounded_amount=unrounded_change,
                    rounded_amount=rounded_change,
                    broker_account=broker_account,
                    expected_cost=expected_cost)
                if not status.is_success():
                    # TODO: Handle ERRORS.
                    logger.error(f"Error creating OMS order request for {fx_pair}: {status}")
                    continue

                # Submit the order to the OMS. Only do this is the pair trades on this day.
                if order_request:
                    status = self.submit_order(request=order_request)
                    if status.is_error():
                        # TODO: Handle failure. Roll back order request? Submit again later?
                        logger.error(f"Error submitting order for {fx_pair} to OMS: {status}")

                    num_fx_orders += 1
            else:
                logger.debug(f"Not creating an OMS hedge request for {fx_pair} on {time} since it does not trade.")

        logger.debug(f"Done submitting OMS orders for action {company_hedge_action}. "
                    f"There were {num_fx_orders} orders.")

    def cancel_all_orders_for_company(self,
                                      company: CompanyTypes) -> ActionStatus:
        if not self.has_open_orders(company):
            return ActionStatus.no_change("No open orders to close for company")
        raise NotImplementedError

    def has_open_orders(self,
                        company: CompanyTypes) -> bool:
        """ Check if a company has any open orders """
        raise NotImplementedError

    def has_unreconciled_orders_for_action(self,
                                           company_hedge_action: CompanyHedgeAction,
                                           account_type: Account.AccountType) -> bool:
        """ Check if a company has any open orders """
        raise NotImplementedError

    def submit_order(self,
                     request: OMSOrderRequest) -> ActionStatus:
        """
        Submit an order to the OMS.
        """
        if request is None:
            return ActionStatus.log_and_no_change("Request was None, no order submitted to OMS")
        if request.requested_amount == 0:
            return ActionStatus.log_and_no_change("Request order size is zero, no order submitted to OMS")
        return self._order_service.submit_orders((request.to_order_ticket(),))

    def reconcile_company_orders_for_account_type(self,
                                                  account_type: Account.AccountType,
                                                  company_hedge_action: CompanyHedgeAction,
                                                  spot_fx_cache: SpotFxCache) -> ActionStatus:
        """
        Do the order reconciliation for a company, determining how to allocate purchased FX back to the individual
        accounts.
        """
        logger.debug(f"Reconciling orders for company: {company_hedge_action.company}, account type: {account_type}")
        if not company_hedge_action:  # Get the latest hedge action
            return ActionStatus.log_and_error("Need a company hedge action to reconcile orders.")

        if not Account.has_account_of_type(company=company_hedge_action.company, account_type=account_type):
            return ActionStatus.log_and_no_change(f"No accounts of type {account_type} to reconcile.")

        if not self.are_tickets_from_hedge_complete(company_hedge_action=company_hedge_action,
                                                    account_type=account_type):
            # TODO: we need to decide if this is an error... depends on how we want to use this method, e.g. if
            #  we only ever reconcile when we are sure the hedge is done, then its an error.
            #
            # TODO: maybe try closing them first
            return ActionStatus.log_and_error("The OMS is not yet done filling the orders")
        logger.debug(f"All tickets related to the hedge are complete.")

        # Find all account level hedge requests.
        account_hedge_requests = self._account_hedge_request_service.get_account_hedge_requests_by_fxpair(
            company_hedge_action=company_hedge_action, account_types=(account_type,))

        if len(account_hedge_requests) == 0:
            return ActionStatus.log_and_success(f"No hedge requests to reconcile of account type {account_type} "
                                                f"for company {company_hedge_action.company.name}.")

        # TODO: What to do if some orders are closed and some are open?
        # Check if the orders are already closed.
        num_open_requests = 0
        for fxpair, requests in account_hedge_requests.items():
            for request in requests:
                if request.status == AccountHedgeRequest.OrderStatus.OPEN:
                    num_open_requests += 1

        if num_open_requests == 0:
            return ActionStatus.log_and_success(f"All hedge requests are already closed.")

        # Query OMS for the FINAL filled amounts. We only reach this point once we are done trying to fill
        filled_amounts = self.get_filled_amount_per_fx_pair_for_company(company_hedge_action,
                                                                        account_type=account_type,
                                                                        spot_cache=spot_fx_cache)

        logger.debug(f"Reconciling orders.")
        return self._reconciliation.reconcile_with_actual_positions(company_hedge_action=company_hedge_action,
                                                                    filled_amounts=filled_amounts,
                                                                    spot_fx_cache=spot_fx_cache,
                                                                    account_hedge_requests=account_hedge_requests,
                                                                    account_type=account_type)

    def reconcile_company_orders(self,
                                 company_hedge_action: CompanyHedgeAction,
                                 spot_fx_cache: SpotFxCache,
                                 ) -> Tuple[ActionStatus, Set[Account.AccountType]]:
        """
        Reconcile company orders for each account type (e.g. live, demo).
        """
        if not company_hedge_action:
            return ActionStatus.log_and_no_change(f"Company has never initiated a hedge"), set({})
        logger.debug(f"Reconciling OMS company orders for {company_hedge_action.company}")

        error_accounts = set()
        had_any_error = False
        for account_type in self.hedgeable_account_types:
            had_error = False
            try:
                action_status = self.reconcile_company_orders_for_account_type(
                    company_hedge_action=company_hedge_action,
                    account_type=account_type,
                    spot_fx_cache=spot_fx_cache)
                if action_status.is_error():
                    had_error, had_any_error = True, True
            except Exception as ex:
                logger.error(f"Exception reconciling orders for account type {account_type}: {ex}")
                had_error, had_any_error = True, True

            if had_error:
                error_accounts.add(account_type)

        if had_any_error:
            return ActionStatus.log_and_error("Error reconciling some account types"), error_accounts

        return ActionStatus.log_and_success(f"Done Reconciling company orders for {company_hedge_action.company}"), \
               error_accounts

    def are_tickets_from_hedge_complete(self,
                                        company_hedge_action: CompanyHedgeAction,
                                        account_type: Account.AccountType) -> bool:
        if account_type == Account.AccountType.LIVE:
            if not Account.has_live_accounts(company=company_hedge_action.company):
                return True

            return self._order_service.are_company_orders_done(company_hedge_action=company_hedge_action)
        else:
            # Non live (e.g. DEMO) accounts do not use the Order Service, so they do not need to wait for the order
            # service to complete.
            return True

    def get_filled_amount_per_fx_pair_for_company(self,
                                                  company_hedge_action: CompanyHedgeAction,
                                                  account_type: Account.AccountType,
                                                  spot_cache: SpotFxCache,
                                                  ) -> Optional[Dict[FxPair, OMSOrderTicket]]:
        # TODO: Make this return Dict[FxPair, OMSOrderTicket] and use OMSOrderTicket throughout the program.

        if account_type == Account.AccountType.LIVE:
            # Get filled amount from tickets.
            try:
                orders = self._order_service.get_orders_from_hedge_action(company_hedge_action=company_hedge_action)
            except Exception:
                # Error reaching the OMS
                logger.error(f"Could not reach the OMS to execute get_filled_amount_per_fx_pair_for_company. "
                             f"Returning None.")
                return None

            fills: Optional[Dict[FxPairInterface, OMSOrderTicket]] = {}
            for order in orders:
                fills[order.fx_pair] = order

            return fills
        else:
            # Demo account. We assume everything was filled, up to lot size rounding.
            hedge_requests = self._account_hedge_request_service.get_account_hedge_requests_by_fxpair(
                company_hedge_action=company_hedge_action,
                account_types=(Account.AccountType.DEMO,))

            if len(hedge_requests) == 0:
                return {}

            market_converter = self._convention_service.make_fx_market_converter()
            # Set the rate at which we got them filled to the spots as of the cut time
            demo_fills = {}
            for fx_pair, account_requests in hedge_requests.items():
                total_amount = 0
                for req in account_requests:
                    total_amount += req.requested_amount
                # Round the total amount.
                amount_filled = market_converter.round_to_lot(fx_pair=fx_pair, amount=total_amount)
                rate = spot_cache.get_fx(fx_pair=fx_pair, value_if_missing=np.nan)

                demo_fills[fx_pair] = OMSOrderTicket(fx_pair=fx_pair,
                                                     company_hedge_action=company_hedge_action,
                                                     amount_filled=amount_filled,
                                                     amount_remaining=0,
                                                     average_price=rate,
                                                     commission=0,
                                                     cntr_commission=0,
                                                     state=OMSOrderTicket.States.FILLED)
            return demo_fills


class BacktestOMSHedgeService(OMSHedgeService):

    def __init__(self,
                 reconcilation: Reconciliation = Reconciliation(),
                 account_hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService(),
                 calendar_service: CalendarService = CalendarService(),
                 convention_service: FxMarketConventionService = FxMarketConventionService(),
                 order_service: OrderServiceInterface = BacktestOrderService()):
        super().__init__(reconcilation=reconcilation,
                         account_hedge_request_service=account_hedge_request_service,
                         calendar_service=calendar_service,
                         convention_service=convention_service,
                         order_service=order_service)


