import logging
from django_bulk_load import bulk_update_models

from main.apps.marketdata.models.fincal.tradingholidays import TradingHolidaysFincal, TradingHolidaysInfoFincal

logger = logging.getLogger(__name__)


class TradingHolidaysForeignkeyReplacer(object):

    def execute(self):
        holidays = TradingHolidaysFincal.objects.all()

        for holiday in holidays:
            code = TradingHolidaysInfoFincal.objects.get(pk=holiday.code)
            if code:
                holiday.code = code.code

        updated = bulk_update_models(
            models=holidays,
            pk_field_names=['id'],
            return_models=True
        )

        logger.debug(f"{len(updated)} data updated.")
