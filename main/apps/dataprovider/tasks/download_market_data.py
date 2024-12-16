from celery import shared_task


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=2,
    name='download_market_data',
    tags=['eod', 'data']  # Add this line
)
def download_market_data(self):
    import logging
    import time
    from main.apps.dataprovider.services.downloader.data_downloader import DataDownloader

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()
    try:
        logger.debug(f"[download_market_data] Running download_market_data")
        data_downloader = DataDownloader()
        data_downloader.execute()
        logger.debug("[download_market_data] download_market_data executed successfully!")
    except Exception as ex:
        logger.exception(f"[download_market_data] Error executing download_market_data: {ex}")
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[download_market_data] Execution time for download_market_data: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(
    bind=True, 
    time_limit=10 * 60, 
    max_retries=2,
    tags=['eod', 'data'],
    name='download_market_data_by_profile'
)
def download_market_data_by_profile(self, profile_id:int):
    import logging
    import time

    from main.apps.dataprovider.models.profile import Profile
    from main.apps.dataprovider.services.downloader.data_downloader import DataDownloaderByProfile

    logger = logging.getLogger("root")

    try:
        profile = Profile.objects.get(pk=profile_id)
    except Profile.DoesNotExist as e:
        logger.error(f"[import_market_data] Profile with id {profile_id} does not exist.")
        return

    # Start timing
    start_time = time.time()
    try:
        logger.debug(f"[download_market_data_by_profile] Running download_market_data_by_profile for profile {profile_id}")
        data_downloader_by_profile = DataDownloaderByProfile(profile=profile)
        data_downloader_by_profile.execute()
        logger.debug(f"[download_market_data_by_profile] download_market_data_by_profile executed successfully for profile {profile_id}!")
    except Exception as ex:
        logger.exception(f"[download_market_data_by_profile] Error executing download_market_data_by_profile for profile {profile_id}: {ex}")
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[download_market_data_by_profile] Execution time for download_market_data_by_profile for profile {profile_id}: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
