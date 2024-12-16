from django.conf import settings

from main.apps.oems.services.connector.oems.base import OEMSBaseAPIConnector


class OEMSEngineAPIConnector(OEMSBaseAPIConnector):
    AUTH = (settings.OEMS_USER, settings.OEMS_PASSWORD)

    def _get_request_url(self, path: str) -> str:
        url = settings.OEMS_URL
        if settings.OEMS_PORT:
            url = f"{url}:{settings.OEMS_PORT}"
        return f"{url}/{self.API_PREFIX}/{path}"

    # ============================================================================
    #  Server Health
    # ============================================================================

    def oms_health(self) -> dict:
        return self._request(path="oms/health")

    def ems_health(self) -> dict:
        return self._request(path="ems/health")

    def fix_health(self) -> dict:
        return self._request(path="fix/health")

    # ============================================================================
    #  Send Tickets
    # ============================================================================

    """
    NOTE:
    These are the only endpoints that any client should be using to directly
    interact with the OMS/EMS/FIX infrastructure (aside from health endpoints).
    """

    def send_new_ticket(self, ticket: dict) -> dict:
        return self._request(path="oms/ticket/new", data=ticket, method="post")

    def cancel_ticket(self, ticket_id: int) -> dict:
        data = {'TicketId': ticket_id}
        return self._request(path="oms/ticket/cancel", data=data)

    def modify_ticket(self, ticket: dict) -> dict:
        return self._request(path="oms/ticket/modify", data=ticket)
