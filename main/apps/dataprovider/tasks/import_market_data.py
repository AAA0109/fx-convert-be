from celery import shared_task, group


@shared_task(
    bind=True, 
    time_limit=30 * 60, 
    max_retries=2,
    name='import_market_data',
    tags=['eod', 'data']  # Add this line
)
def import_market_data(self, profile_id, ignore_days=False, company_id=None, fxpair_id=None):
    from django.core.exceptions import ObjectDoesNotExist
    from hdlib.DateTime.Date import Date
    import logging
    logger = logging.getLogger("root")

    from main.apps.dataprovider.models import Profile
    from main.apps.dataprovider.services.importer.data_importer import DataImporter
    import time
    # Start timing
    start_time = time.time()

    weekday = Date.now(tz=Date.timezone_NY).weekday()
    try:
        run_options = {
            "company_id": company_id,
            "fxpair_id": fxpair_id
        }

        logger.debug(
            f"[import_market_data] Running market data importer for "
            f"profile_id={profile_id} (ignore_days={ignore_days}) "
            f"with following configurations: {run_options}")

        try:
            profile = Profile.objects.get(pk=profile_id)
        except ObjectDoesNotExist:
            logger.error(f"[import_market_data] Profile with id {profile_id} does not exist.")
            return

        if ignore_days or str(weekday) in profile.days:
            logger.debug(f"[import_market_data] Importing market data for {profile.name} "
                        f"(profile_id={profile.pk}, ignore_days={ignore_days})")

            data_importer = DataImporter(profile.pk, options=run_options)
            data_importer.execute()

        logger.debug("[import_market_data] Market data import task executed successfully!")
    except Exception as ex:
        logger.exception(f"[import_market_data] Error executing market data import task: {ex}")
        # Ensuring that the exception is logged with stack trace for better debugging
        # Reraise the exception to let Celery handle retries or failure logging
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[import_market_data] Execution time for import_market_data: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(time_limit=30 * 60, max_retries=2)
def import_market_data_with_options(profile_id, ignore_days=False):
    import time
    from main.apps.dataprovider.models.profile import ProfileParallelOption
    import logging
    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        option = ProfileParallelOption.objects.filter(profile_id=profile_id).first()
        if not option:
            logger.error(f"[import_market_data_with_options] No options found for profile_id={profile_id}")
            return

        field = option.field
        ids = option.generate_dynamic_ids() if option else []

        tasks = [import_market_data.s(profile_id, ignore_days, **{field: _id}) for _id in ids]
        group(*tasks).apply_async()
    except Exception as ex:
        logger.exception(f"[import_market_data_with_options] Failed to initiate market data import "
                         f"with options for profile_id={profile_id}: {ex}")
        # It's critical to raise the exception to ensure Celery is aware of the failure
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[import_market_data_with_options] Execution time for "
                    f"import_market_data_with_options: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
