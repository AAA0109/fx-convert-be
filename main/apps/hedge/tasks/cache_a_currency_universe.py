import logging
import time

from celery import shared_task
from hdlib.DateTime.Date import Date

from main.apps.currency.models import Currency
from main.apps.hedge.services.hedger import caching_make_cntr_currency_universe

logger = logging.getLogger("root")


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=3,
    name='cache_currency_universe',
    tags=['eod']  # Add this line
)
def cache_currency_universe(self, currency_id: int, ref_date: str):
    start_time = time.time()

    try:
        # Parse the reference date
        ref_date = Date.from_str(ref_date)

        logger.debug(f"Running cache_a_currency_universe for currency (ID={currency_id}) and ref_date {ref_date}")

        # Fetch the currency instance
        domestic = Currency.objects.get(pk=currency_id)

        # Perform the caching operation
        caching_make_cntr_currency_universe(domestic=domestic, ref_date=ref_date, bypass_errors=True)

        logger.debug(f"Finished cache_a_currency_universe for currency (ID={currency_id}) and ref_date {ref_date}")
        logger.debug("[cache_currency_universe] Command executed successfully!")

    except Exception as ex:
        logger.error(f"[cache_currency_universe] Error during caching: {ex}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[cache_currency_universe] Execution time: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
