import logging
import time

from celery import shared_task

from main.apps.marketdata.services.estimators.fxspotvol import FxSpotVolEstimatorCreator

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    time_limit=20 * 60,
    max_retries=2,
    name='create_fxspot_vol_estimator',
    tags=['eod']  # Add this line
)
def create_fxspot_vol_estimator(self, pair_id):
    start_time = time.time()

    try:
        tag = "Covar-Prod"
        fx_spot_vol_estimator_creator = FxSpotVolEstimatorCreator(
            tag=tag, pair_id=pair_id)
        fx_spot_vol_estimator_creator.execute()

        logger.debug(
            "[create_fxspot_vol_estimator] FxSpot volatility estimator executed successfully!")

    except Exception as e:
        logger.error(
            f"[create_fxspot_vol_estimator] Error while running the FxSpot volatility estimator: {e}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(
            f"[create_fxspot_vol_estimator] Execution time: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
