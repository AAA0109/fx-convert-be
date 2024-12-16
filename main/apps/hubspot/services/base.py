from abc import ABC
from hubspot import HubSpot
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class HubSpotBaseService(ABC):
    client: HubSpot

    def __init__(self):
        self.client = HubSpot(access_token=settings.HUBSPOT_ACCESS_TOKEN)

    def log_and_raise_error(self, e: Exception):
        logging.error(e)
        raise e
