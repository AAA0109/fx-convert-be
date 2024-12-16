import easyib
from django.conf import settings

class ClientPortalApi():
    """
    Connector class for interacting with IBKR Client Portal API
    """
    def get_client(self) -> easyib.REST:
        self.api = easyib.REST(url=f'{settings.IB_CLIENT_PORTAL_URL}:{settings.IB_CLIENT_PORTAL_PORT}')
        return self.api
