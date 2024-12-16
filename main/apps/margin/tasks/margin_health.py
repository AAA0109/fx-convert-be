import logging
import time

from celery import shared_task

from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.margin.services.margin_health import MarginHealthService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=2,
    name='check_margin_health',
    tags=['eod']  # Add this line
)
@decorator_to_post_exception_message_on_slack()
def check_margin_health(self, company_id, deposit_required_level=0.5):
    start_time = time.time()

    try:
        margin_health = MarginHealthService(company_id=company_id,
                                            deposit_required_level=deposit_required_level)
        margin_health.execute()
        logger.debug("[check_margin_health] Margin health check executed successfully!")

    except Exception as e:
        logger.error(f"[check_margin_health] Error while checking margin health: {e}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[check_margin_health] Execution time: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
