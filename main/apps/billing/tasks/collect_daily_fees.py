import logging
import time
from typing import Optional

from celery import shared_task

from main.apps.billing.services.daily_fee import DailyFeeService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=2,
    name='collect_daily_fees',
    tags=['eod']  # Add this line
)
def collect_daily_fees(self, company_id: Optional[int] = None):
    start_time = time.time()

    try:
        daily_fee_service = DailyFeeService(company_id)
        daily_fee_service.execute()
        logger.debug("[collect_daily_fees] Command executed successfully!")

    except Exception as ex:
        logger.error(f"[collect_daily_fees] Error while collecting fees: {ex}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[collect_daily_fees] Execution time for collecting daily fees: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
