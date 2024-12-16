import logging
from typing import List
from celery import shared_task, group

from main.apps.dataprovider.models import File, Profile


def _process_csv(self):
    query_set = File.objects.filter(
        status__in=[File.FileStatus.DOWNLOADED, File.FileStatus.ERROR, File.FileStatus.PREPROCESSED],
        profile__enabled=True,
        source__enabled=True,
        data_provider__enabled=True,
        profile__file_format=Profile.FileFormat.CSV,
        profile__target__isnull=False
    )
    if self.profile_id is not None:
        query_set = query_set.filter(profile_id=self.profile_id)
    for downloaded_file in query_set:
        profile = downloaded_file.profile
        logging.info(f"Starting import for profile: {profile.id}")
        try:
            downloaded_file.status = File.FileStatus.PREPROCESSING
            downloaded_file.save()
            fpath = self._get_filepath(downloaded_file, 'csv')
            self._import_csv(fpath=fpath, profile=profile)
            downloaded_file.status = File.FileStatus.PREPROCESSED
            downloaded_file.save()
        except Exception as e:
            downloaded_file.status = File.FileStatus.ERROR
            downloaded_file.save()
            logging.error(e)
            raise e


@shared_task(bind=True, time_limit=2 * 60 * 60, max_retries=2)
def backfill_marketdata_by_profile_id(self, profile_id:int):
    import time

    from main.apps.dataprovider.services.importer.data_importer import DataImporter

    logger = logging.getLogger("root")

    DataImporter._process_csv = _process_csv

    run_options = {
        "company_id": None,
        "fxpair_id": None
    }

    start_time = time.time()

    logger.info(f"[backfill_marketdata_by_profile_id] Backfill market data for profile id {profile_id}")

    try:
        data_importer = DataImporter(profile_id, options=run_options)
        data_importer.execute()

        logger.debug("[backfill_marketdata_by_profile_id] Backfill market data task executed successfully!")
    except Exception as ex:
        logger.exception(f"[backfill_marketdata_by_profile_id] Error executing backfill market data task: {ex}")
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[backfill_marketdata_by_profile_id] Execution time for backfill_marketdata_by_profile_id: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(time_limit=2 * 60 * 60, max_retries=2)
def backfill_marketdata_for_profile_ids(profile_ids:List[int]):
    import time

    logger = logging.getLogger("root")

    start_time = time.time()

    logger.info(f"[backfill_marketdata_for_profile_ids] Backfill market data for profile ids {profile_ids}")

    try:
        backfill_tasks = [backfill_marketdata_by_profile_id.si(profile_id=id) for id in profile_ids]
        group(*backfill_tasks).apply_async()

        logger.debug("[backfill_marketdata_for_profile_ids] Backfill market data task executed successfully!")
    except Exception as ex:
        logger.exception(f"[backfill_marketdata_for_profile_ids] Error executing backfill market data task: {ex}")
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[backfill_marketdata_for_profile_ids] Execution time for backfill_marketdata_for_profile_ids: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
