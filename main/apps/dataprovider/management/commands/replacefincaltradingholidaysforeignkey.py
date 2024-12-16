import logging
from django.core.management.base import BaseCommand

from main.apps.dataprovider.scripts.patch_scripts.fincal.tradingholidays_foreignkey_replacer import TradingHolidaysForeignkeyReplacer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Replace fincal trading holidays foreign key column'

    def handle(self, *args, **options):
        try:
            foreignkey_replacer = TradingHolidaysForeignkeyReplacer()
            foreignkey_replacer.execute()
        except Exception as e:
            logging.error(f"{e}")

