from django.conf import settings

from main.apps.oems.services.connector.oems.base import OEMSBaseAPIConnector


class OEMSQueryAPIConnector(OEMSBaseAPIConnector):
    AUTH = (settings.OEMS_API_USER, settings.OEMS_API_PASSWORD)

    def _get_request_url(self, path: str) -> str:
        url = settings.OEMS_API_URL
        if settings.OEMS_API_PORT:
            url = f"{url}:{settings.OEMS_API_PORT}"
        return f"{url}/{self.API_PREFIX}/{path}"

    # ============================================================================
    #  Get Ticket
    # ============================================================================

    """
    NOTE / TODO TODO TODO
    These endpoints were setup for testing but should not be used in production.
    An API that reads from the database into Django will be necessary and specific queries
    will be required by use case. A common query that will needed is:
        Get all active tickets (by account/by company/by hedgeactionid/etc.)
        Get all finished tickets since {date}
    Everything below should be re-implemented properly.
    """

    def get_tickets(self) -> list:
        return self._request(path="oms/tickets")

    def get_tickets_by_id(self, ticket_id: int) -> dict:
        return self._request(path=f"oms/tickets/{ticket_id}")

    def get_tickets_by_hedge_action(self, hedge_action_id: int) -> dict:
        return self._request(path=f"oms/tickets/hedgeactionid/{hedge_action_id}")

    def get_tickets_by_account(self, account: int) -> dict:
        return self._request(path=f"oms/tickets/account/{account}")

    def get_tickets_by_company(self, company: int) -> dict:
        return self._request(path=f"oms/tickets/company/{company}")

    # ============================================================================
    #  Get Order
    # ============================================================================

    def get_orders(self) -> dict:
        return self._request(path="oms/orders")

    def get_orders_by_hedge_action(self, hedge_action_id: int) -> dict:
        return self._request(path=f"oms/orders/hedgeactionid/{hedge_action_id}")

    def get_orders_by_account(self, account: int) -> dict:
        return self._request(path=f"oms/orders/account/{account}")

    def get_orders_by_company(self, company: int) -> dict:
        return self._request(path=f"oms/orders/company/{company}")

    def get_orders_by_ticket_id(self, ticket_id: int):
        # NOTE(Nate): Is this an error, or are hedge_action_id and ticker_id the same?
        #  (see get_orders_by_hedge_action).
        return self._request(path=f"oms/orders/hedgeactionid/{ticket_id}")

    def get_orders_by_id(self, order_id: int):
        return self._request(path=f"oms/orders/orderid/{order_id}")

    # ============================================================================
    #  Get Fills
    # ============================================================================

    def get_fills(self) -> list:
        return self._request(path="oms/fills")

    def get_fills_by_ticket_id(self, ticket_id: int) -> dict:
        return self._request(path=f"oms/fills/ticketid/{ticket_id}")

    def get_fills_by_order_id(self, order_id: int) -> dict:
        return self._request(path=f"oms/fills/orderid/{order_id}")

    def get_fills_by_id(self, fill_id: int) -> dict:
        return self._request(path=f"oms/fills/fillid/{fill_id}")
