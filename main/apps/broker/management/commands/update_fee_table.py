import logging

from django.core.management.base import BaseCommand
from main.apps.broker.services.broker_fee_updater import BrokerFeeUpdater


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update Currency Fee data using Fee Template table'

    def handle(self, *args, **options):
        try:
            fee_updater = BrokerFeeUpdater()
            fee_updater.update_broker_fee_data()
            logging.info("Success updating currency fee data")
        except Exception as e:
            logging.error(f"Error updating currency fee data: {e}", exc_info=True)
