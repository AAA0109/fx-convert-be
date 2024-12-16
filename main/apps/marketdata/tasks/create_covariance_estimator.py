import logging
import time

from celery import shared_task

from main.apps.marketdata.services.estimators.covariance import CovarianceEstimatorCreator

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, 
    time_limit=30 * 60, 
    max_retries=2,
    name='create_covariance_estimator',
    tags=['eod']  # Add this line
)
def create_covariance_estimator(self, pair1_id, pair2_id=None, parameters=0.99, min_date=None):
    start_time = time.time()

    try:
        tag = "Covar-Prod"
        logger.debug(
            f"Running covariance estimator (tag={tag}) for "
            f"pair1={pair1_id} and pair2={pair2_id or 'all pairs'}, "
            f"parameters={parameters}, min_date={min_date}")

        covariance_estimator_creator = CovarianceEstimatorCreator(
            pair1=pair1_id,
            pair2=pair2_id,
            tag=tag,
            parameters=parameters,
            min_date=min_date
        )
        covariance_estimator_creator.execute()

        logger.debug("[create_covariance_estimator] Covariance estimator executed successfully!")

    except Exception as e:
        logger.error(f"[create_covariance_estimator] Error while running the covariance estimator: {e}")
        # Reraise the exception to let Celery handle retries or failure logging
        raise

    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[create_covariance_estimator] Execution time: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
