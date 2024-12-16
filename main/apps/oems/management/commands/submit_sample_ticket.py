import logging

from django.core.management.base import BaseCommand

from main.apps.oems.services.connector.oems import OEMSEngineAPIConnector

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to submit a sample ticket"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        # parser.add_argument("--oms_health", type=int, help="Optional: Check OMS health (Default=True)")

    def handle(self, *args, **options):
        sample_ticket: dict = {
            "Market": "USDSGD",
            "Side": "Buy",
            "TicketType": "OPEN",
            "Qty": 2000000,
            "HedgeActionId": 101,
            "Account": "DU5666110",
            "Company": 1,
            "SubDest": "IBKR_FIX"
        }

        try:
            oems_engine_api: OEMSEngineAPIConnector = OEMSEngineAPIConnector()
            logger.debug(f"Submitting a sample ticket", sample_ticket)
            response = oems_engine_api.send_new_ticket(ticket=sample_ticket)
            if response['type'] != "SUCCESS":
                logger.error("Failed to submit a sample ticket")
            logger.debug(response)
            logger.debug("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
