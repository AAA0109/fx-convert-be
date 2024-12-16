import logging
from abc import ABCMeta, abstractmethod
from typing import List, Optional, Sequence, Dict, Tuple

from hdlib.Core import FxPairInterface
from hdlib.Core.FxPair import FxPair as FxPairHDL

from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.hedge.models import CompanyHedgeAction, OMSOrderRequest
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.oems.services.connector.oems import OEMSEngineAPIConnector, OEMSQueryAPIConnector
from main.apps.oems.support.tickets import OMSOrderTicket, OrderTicket
from main.apps.util import ActionStatus

logger = logging.getLogger(__name__)


class OrderServiceInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> List[OMSOrderTicket]:
        """
        Get all orders, as OMSOrderTickets, associated with a particular hedge action.
        """
        pass

    @abstractmethod
    def complete_oms_order_requests(self, company_hedge_action: CompanyHedgeAction):
        """
        Finds all the OMSOrderRequests for a particular hedge action, gets the OMSOrderTickets tickets summarizing the
        trading, and uses that to fill in the missing information in the OMSOrderRequests (e.g. filled amounts)
        """
        pass

    @abstractmethod
    def get_tickets_without_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> list:
        """
        Get all tickets that have not yet generated orders.
        """
        pass

    @abstractmethod
    def submit_orders(self, orders: Sequence[OrderTicket]) -> ActionStatus:
        """
        Submit an iterable collection of OrderTickets to the OMS. The OrderTickets are converted into dictionaries
        and those are each sent to the OemsApi, which does the actual communication with the OMS.
        """
        pass

    @abstractmethod
    def are_company_orders_done(self, company_hedge_action: Optional[CompanyHedgeAction] = None,
                                company: Optional[Company] = None) -> bool:
        """
        Returns whether all orders associated with a company hedge action are in a finished state. Note that orders
        can fail to fill even when they leave the unfinished state, e.g. they can be rejected for insufficient margin.
        """
        pass


class OrderService(OrderServiceInterface):
    """
    Class responsible to submitting orders and checking the status of orders.
    """

    @staticmethod
    def can_connect():
        """
        Check if the OEMS API can connect.
        """
        oems_engine_api = OEMSEngineAPIConnector()
        try:
            oems_engine_api.oms_health()
        except Exception:
            return False
        return True

    def get_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> List[OMSOrderTicket]:
        """
        Get all orders, as OMSOrderTickets, associated with a particular hedge action.
        """
        oems_query_api = OEMSQueryAPIConnector()
        orders = oems_query_api.get_orders_by_hedge_action(hedge_action_id=company_hedge_action.id)

        # Example order, orders is a list of dictionaries like this:
        # {
        #   'Market': 'USDJPY',
        #   'HedgeActionId': 101,
        #   'TicketId': 1,
        #   'OrderId': 2,
        #   'Side': 'Buy',
        #   'Qty': 100.0,
        #   'Account': 1,
        #   'Company': 1,
        #   'InternalAlgo': 'LIQUID_TWAP1',
        #   'TIF': 'GTC',
        #   'StartTime': None,
        #   'EndTime': None,
        #   'OrderLength': None,
        #   'LimitPrice': None,
        #   'StopPrice': None,
        #   'Staged': None,
        #   'RefTicket': None,
        #   'RefPrice': None,
        #   'BaseCcy': 'USD',
        #   'CntrCcy': 'JPY',
        #   'Source': 'INTERNAL_OMS',
        #   'Dest': 'INTERNAL_EMS',
        #   'SubDest': 'IBKR_FIX',
        #   'Trader': None,
        #   'CreateTime': '2022-05-12T02:17:13.784628',
        #   'State': 'FILLED',
        #   'StateStart': '2022-05-12T02:17:23.822227',
        #   'RemainQty': 0.0,
        #   'Done': 100.0,
        #   'CntrDone': 11597.547013593077,
        #   'Commission': 0.0,
        #   'CntrCommission': 0.0,
        #   'AvgPrice': 115.9754701359,
        #   'Saved': True
        #   }

        output = []
        for order in orders:
            output.append(OrderService._make_order_ticket_from_dict(order))

        return output

    def get_tickets_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> Optional[
        List[OMSOrderTicket]]:
        # TODO: Return some sort of ticket object.
        oems_query_api = OEMSQueryAPIConnector()
        try:
            tickets = oems_query_api.get_tickets_by_hedge_action(hedge_action_id=company_hedge_action.id)
        except Exception:
            # Likely, the API could not connect.
            return None

        order_tickets = []
        for ticket in tickets:
            order_tickets.append(OrderService._make_order_ticket_from_dict(ticket))
        return order_tickets

    def complete_oms_order_requests(self, company_hedge_action: CompanyHedgeAction):
        """
        Finds all the OMSOrderRequests for a particular hedge action, gets the OMSOrderTickets tickets summarizing the
        trading, and uses that to fill in the missing information in the OMSOrderRequests (e.g. filled amounts)
        """
        logger.debug(f"Completing OMS order requests (filling in data from trades)")

        requests = list(OMSOrderRequest.get_requests_for_action(company_hedge_action=company_hedge_action))
        if len(requests) == 0:
            logger.debug(f"There were no OMS order requests to complete.")
            return
        logger.debug(f"There are {len(requests)} OMS order requests to complete for hedge action "
                    f"{company_hedge_action.id}")

        # Convert tickets to map from Fx pair to ticket.
        ticket_list = [ticker for ticker in self.get_tickets_from_hedge_action(company_hedge_action)]
        if ticket_list:
            tickets = {tk.fx_pair: tk for tk in ticket_list}
        else:
            tickets = {}

        logger.debug(f"Found {len(ticket_list)} order tickets.")

        # "Complete" the OMS order requests by filling in all the data from the tickets.
        for req in requests:
            # Try to find the OMSOrderTicket for the request.
            tk: OMSOrderTicket = tickets.get(req.pair, None)
            if tk is not None:
                logger.debug(f"  * Updating OMSOrderRequest for {req.pair}: "
                            f"filled_amount = {tk.amount_filled}, "
                            f"total_price = {tk.total_price}, "
                            f"commission = {tk.commission}, "
                            f"cntr commission = {tk.cntr_commission}")
                req.filled_amount = tk.amount_filled
                req.total_price = tk.total_price
                req.commission = tk.commission
                req.cntr_commission = tk.cntr_commission
                # Very important - save the request updates.
                req.save()
            else:
                logger.warning(f"  => Could not find an OMSOrderTicket for fx pair {req.pair}, "
                               f"hedge action id = {company_hedge_action.id}")
        logger.debug(f"Done completing OMS order requests.")

    def get_tickets_without_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> list:
        """
        Get all tickets that have not yet generated orders.
        """
        oems_query_api = OEMSQueryAPIConnector()
        tickets = oems_query_api.get_tickets_by_hedge_action(hedge_action_id=company_hedge_action.id)
        orders = oems_query_api.get_orders_by_hedge_action(hedge_action_id=company_hedge_action.id)

        orders_tickets = set({})
        for order in orders:
            orders_tickets.add(order["TicketId"])

        output = []
        for ticket in tickets:
            if ticket["TicketId"] not in orders_tickets:
                output.append(ticket)
        # TODO: Return some sort of ticket object.
        return output

    def submit_orders(self, orders: Sequence[OrderTicket]) -> ActionStatus:
        """
        Submit an iterable collection of OrderTickets to the OMS. The OrderTickets are converted into dictionaries
        and those are each sent to the OemsApi, which does the actual communication with the OMS.
        """
        oems_engine_api = OEMSEngineAPIConnector()
        count, errors = 0, []
        for order in orders:
            try:
                count += 1
                ticket_dict = order.make_dict()
                logger.debug(
                    f"OMSService: submitting order ({count} / {len(orders)} in this batch) via OemsApi: {ticket_dict}")
                reply = oems_engine_api.send_new_ticket(ticket_dict)
                if reply["Type"] == "ERROR":
                    errors.append(f"Ticket was {reply['Action']}, reason: {reply['Msg']}")
            except Exception as ex:
                errors.append(f"{ex}")
        if 0 < len(errors):
            return ActionStatus.log_and_error(f"Some errors submitting orders: {errors}")
        return ActionStatus.log_and_success(f"Successfully submitted {count} orders to the OMS")

    def are_company_orders_done(self, company_hedge_action: Optional[CompanyHedgeAction] = None,
                                company: Optional[Company] = None) -> bool:
        """
        Returns whether all orders associated with a company hedge action are in a finished state. Note that orders
        can fail to fill even when they leave the unfinished state, e.g. they can be rejected for insufficient margin.
        """

        if not company_hedge_action and not company:
            raise ValueError("need either a CompanyHedgeAction or Company to check orders for company")
        if company_hedge_action is None:
            company_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company)

        # Otherwise, check that all orders have been fully filled.
        tickets = self.get_tickets_from_hedge_action(company_hedge_action=company_hedge_action)
        logger.debug(f"Checking the state of {len(tickets)} tickets for company {company}, "
                    f"hedge action id = {company_hedge_action.id}")
        all_good = True
        count_unfinished = 0
        for ticket in tickets:
            if ticket.state in OMSOrderTicket.Unfinished:
                logger.debug(f"Ticket for {ticket.fx_pair} is UNFINISHED, state = {ticket.state}")
                all_good = False
                count_unfinished += 1
            else:
                logger.debug(f"Ticket for {ticket.fx_pair} is finished, state = {ticket.state}")
                if ticket.state in OMSOrderTicket.FinishedSuccess:
                    logger.debug(f"Fill was successful.")
                elif ticket.state in OMSOrderTicket.FinishedWarning:
                    logger.debug(f"Fill completed, but with WARNINGS.")
                elif ticket.state in OMSOrderTicket.FinishedFailure:
                    logger.debug(f"Fill completed, but FAILED to actually fill.")
        logger.debug(f"There are {count_unfinished} (of {len(tickets)}) unfinished orders.")
        return all_good

    @staticmethod
    def _make_order_ticket_from_dict(order_ticket: dict) -> OMSOrderTicket:
        multiplier = 1 if order_ticket["Side"] == "Buy" else -1
        company_hedge_action = CompanyHedgeAction.get_action(order_ticket["HedgeActionId"])
        return OMSOrderTicket(fx_pair=FxPairHDL.from_str(order_ticket["Market"]),
                              company_hedge_action=company_hedge_action,
                              amount_filled=multiplier * order_ticket["Done"],
                              amount_remaining=multiplier * order_ticket["RemainQty"],
                              average_price=order_ticket["AvgPrice"],
                              commission=order_ticket["Commission"],
                              cntr_commission=order_ticket["CntrCommission"],
                              state=OrderService._make_state(order_ticket["State"]))

    @staticmethod
    def _make_state(state: str) -> OMSOrderTicket.States:
        """
        Convert the state (string) into a state enum.
        """
        return OMSOrderTicket.States[state]


class BacktestOrderService(OrderServiceInterface):

    def __init__(self,
                 fx_spot_provider: FxSpotProvider = FxSpotProvider()):
        self._orders: Dict[int, List[OMSOrderTicket]] = dict()
        self._cash_position: Dict[Currency, float] = dict()
        self._fx_spot_provider = fx_spot_provider

    def get_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> List[OMSOrderTicket]:
        return self._orders.get(company_hedge_action.id, [])

    def complete_oms_order_requests(self, company_hedge_action: CompanyHedgeAction):
        pass

    def get_tickets_without_orders_from_hedge_action(self, company_hedge_action: CompanyHedgeAction) -> list:
        return []

    def submit_orders(self, orders: Sequence[OrderTicket]) -> ActionStatus:
        for order in orders:
            price = self._fx_spot_provider.get_spot_value(order.fx_pair, date=order.company_hedge_action.time)
            ticket = OMSOrderTicket(fx_pair=order.fx_pair, company_hedge_action=order.company_hedge_action,
                                    amount_filled=order.signed_amount, amount_remaining=0, average_price=price,
                                    commission=0, cntr_commission=0, state=OMSOrderTicket.States.FILLED)
            self._orders.setdefault(order.company_hedge_action.id, []).append(ticket)
            for cny, amount in ticket.cash_position.items():
                self._cash_position.setdefault(cny, 0)
                self._cash_position[cny] += amount
        return ActionStatus.log_and_success(f"Successfully submitted {len(orders)} orders to the OMS")

    def are_company_orders_done(self, company_hedge_action: Optional[CompanyHedgeAction] = None,
                                company: Optional[Company] = None) -> bool:
        return True

    @property
    def cash_positions(self) -> Dict[Currency, float]:
        return self._cash_position
