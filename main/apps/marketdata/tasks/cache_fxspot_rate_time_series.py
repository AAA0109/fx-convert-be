import logging
import time
from datetime import datetime

from celery import shared_task
from django.core.cache import cache

from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=2,
    name='cache_fx_spot_rates',
    tags=['eod']  # Add this line
)
def cache_fx_spot_rates(self, pair_id, min_date=None, timeout=None, delete=True):
    start_time = time.time()

    try:
        max_date = datetime.now().strftime("%Y-%m-%d")
        cache_key = f'fxspot_pair_{pair_id}_rate_ts_on_{max_date}'

        if delete:
            logger.debug(f"Deleting FxSpot (pair={pair_id}) cache for (key={cache_key}).")
            cache.delete(cache_key)

        logger.debug(f"Caching FxSpot rate time series for pair={pair_id}.")
        rate_time_series = FxSpotProvider().get_rate_time_series(fx_pair=pair_id, min_date=min_date)
        cache.set(cache_key, rate_time_series, timeout)

        logger.debug("[cache_fx_spot_rates] FxSpot rates cached successfully!")

    except Exception as e:
        logger.error(f"[cache_fx_spot_rates] Error while caching FxSpot rates: {e}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[cache_fx_spot_rates] Execution time: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
