from celery import shared_task, group

from main.apps.dataprovider.tasks import import_market_data


@shared_task(time_limit=10 * 60, max_retries=2)
def inverse_and_triangulate_market_data(self, profile_id):
    from main.apps.dataprovider.services.backfiller.inverse_triangulator import InverseAndTriangulatorService
    import time
    import logging

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.debug(
            f"[inverse_and_triangulate_market_data] Running inverse_and_triangulate_market_data")
        inverse_triangulator_service = InverseAndTriangulatorService(profile_id=profile_id)
        inverse_triangulator_service.execute()
        logger.debug("[inverse_and_triangulate_market_data] inverse_and_triangulate_market_data task executed successfully!")
    except Exception as ex:
        logger.exception(f"[inverse_and_triangulate_market_data] Error executing inverse_and_triangulate_market_data task: {ex}")
        # Ensuring that the exception is logged with stack trace for better debugging
        # Reraise the exception to let Celery handle retries or failure logging
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[inverse_and_triangulate_market_data] Execution time for inverse_and_triangulate_market_data: {execution_time} seconds")
        return f"{execution_time / 60} minutes"

@shared_task(time_limit=10 * 60, max_retries=2)
def workflow_corpay_spot_forward_import_triangulate_marketdata(spot_profile_id=None, forward_profile_id=None, ignore_days=False):
    import time
    from main.apps.dataprovider.models.profile import ProfileParallelOption
    from celery import chord
    import logging

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        if not spot_profile_id or not forward_profile_id:
            logger.error(f"[import_and_triangulate_corpay_fxdata] spot_profile_id and forward_profile_id must be set")
            return

        spot_options = ProfileParallelOption.objects.filter(profile_id=spot_profile_id).first()
        forward_options = ProfileParallelOption.objects.filter(profile_id=forward_profile_id).first()
        if not spot_options:
            logger.error(f"[import_and_triangulate_corpay_fxdata] No options found for spot_profile_id={spot_profile_id}")
            return

        if not forward_options:
            logger.error(f"[import_and_triangulate_corpay_fxdata] No options found for forward_profile_id={forward_profile_id}")
            return

        spot_field = spot_options.field
        spot_ids = spot_options.generate_dynamic_ids() if spot_options else []

        forward_field = forward_options.field
        forward_ids = forward_options.generate_dynamic_ids() if forward_options else []

        spot_fetch_rate_tasks = [import_market_data.s(spot_profile_id, ignore_days, **{spot_field: _id}) for _id in spot_ids]
        forward_fetch_rate_tasks = [import_market_data.s(forward_profile_id, ignore_days, **{forward_field: _id}) for _id in forward_ids]

        spot_forward_fetch_rate_tasks = group(spot_fetch_rate_tasks + forward_fetch_rate_tasks)
        workflow = chord(spot_forward_fetch_rate_tasks,
                          inverse_and_triangulate_market_data.s(spot_profile_id) | inverse_and_triangulate_market_data.s(forward_profile_id))
        result = workflow.apply_async()
        return result
    except Exception as ex:
        logger.exception(f"[import_and_triangulate_corpay_fxdata] Failed to initiate market data import "
                         f"with options for spot_profile_id={spot_profile_id} and forward_profile_id={forward_profile_id}: {ex}")
        # It's critical to raise the exception to ensure Celery is aware of the failure
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[import_and_triangulate_corpay_fxdata] Execution time for "
                    f"import_and_triangulate_corpay_fxdata: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
