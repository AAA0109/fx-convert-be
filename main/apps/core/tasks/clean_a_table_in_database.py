from celery import shared_task


@shared_task(bind=True, time_limit=10 * 60, max_retries=2)
def clean_a_table_in_database(self, app_label: str, model_name: str, days: int = 30):
    from django.utils import timezone
    from datetime import timedelta
    from django.apps import apps
    import logging
    import time

    logger = logging.getLogger("root")

    start_time = time.time()
    days_ago = timezone.now() - timedelta(days=days)
    days_ago = days_ago.replace(hour=0, minute=0, second=0, microsecond=0)
    deleted_count = 0

    try:

        logger.debug(f"[clean_a_table_in_database] cleaning "
                    f"app_label={app_label}, model_name={model_name}, for days={days}")

        try:
            model = apps.get_model(app_label, model_name)
            query_set = model.objects.filter(created__lt=days_ago)
            logger.debug(f"[clean_a_table_in_database] SQL Query: {query_set.query}")

            deleted_count, _ = query_set.delete()

            logger.debug(f"[clean_a_table_in_database] deleted {deleted_count} records "
                        f"from {app_label}.{model_name} older than {days} days")
        except LookupError:
            logger.error(f"[clean_a_table_in_database] model {model_name} in app {app_label} does not exist.")
            return
        logger.debug(f"[clean_a_table_in_database] cleaning "
                    f"app_label={app_label}, model_name={model_name}, for days={days} executed successfully!")
    except Exception as ex:
        logger.exception(f"[clean_a_table_in_database] error cleaning "
                         f"app_label={app_label}, model_name={model_name}, for days={days}: {str(ex)}")
        raise
    finally:

        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[clean_a_table_in_database] execution time for "
                    f"cleaning app_label={app_label}, model_name={model_name}, "
                    f"for days={days}: {execution_time / 60} minutes")
        return f"Deleted {deleted_count} in {execution_time / 60} minutes"
