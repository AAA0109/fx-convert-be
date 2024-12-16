from celery import shared_task


@shared_task(bind=True, time_limit=10 * 60, max_retries=2)
def simple_activity_report_for_a_model(
    self,
    app_label: str,
    model_name: str,
    frequency: str = 'daily',  # Added frequency parameter with default value
    columns: list[str] = None,
    filters: list[str] = None,
    excludes: list[str] = None,
):
    from django.utils import timezone
    from datetime import timedelta
    from django.apps import apps
    import logging
    import time
    import csv
    import tempfile
    from google.cloud import storage
    from django.conf import settings

    logger = logging.getLogger("root")
    start_time = time.time()

    # Determine the date range based on the frequency
    if frequency == 'daily':
        start_date = timezone.now() - timedelta(days=1)
    elif frequency == 'weekly':
        start_date = timezone.now() - timedelta(weeks=1)
    elif frequency == 'monthly':
        start_date = timezone.now() - timedelta(days=30)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")

    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date = timezone.now()
    end_date_str = end_date.strftime('%Y-%m-%d')
    file_name = f"{start_date_str}__{end_date_str}.csv"
    gcs_blob: str = f"reports/{frequency}/{model_name}/{file_name}"

    record_count = 0

    try:
        logger.info(f"[simple_activity_report_for_a_model] generating report for {app_label}.{model_name}, "
                    f"from {start_date_str} to {end_date_str}, frequency={frequency}")

        model = apps.get_model(app_label, model_name)
        query_set = model.objects.filter(created__gte=start_date, created__lte=end_date)

        if filters:
            for filter_query in filters:
                key, value = filter_query.split('=')
                query_set = query_set.filter(**{key: value})

        if excludes:
            for exclude_str in excludes:
                key, value = exclude_str.split('=')
                # Handling boolean values properly
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                query_set = query_set.exclude(**{key: value})

        if columns:
            query_set = query_set.values_list(*columns, named=True)
        else:
            if query_set.exists():
                columns = list(query_set.values()[0].keys())  # Ensure to fetch columns if not provided

        logger.info(f"[simple_activity_report_for_a_model] SQL Query: {str(query_set.query)}")
        record_count = query_set.count()

        if record_count > 0:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = f"{temp_dir}/{file_name}"
                with open(output_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(columns)
                    for record in query_set:
                        row = [getattr(record, field) for field in columns]
                        writer.writerow(row)

                storage_client = storage.Client()
                bucket = storage_client.bucket(settings.GS_BUCKET_NAME)
                blob = bucket.blob(gcs_blob)
                blob.upload_from_filename(output_path)

        logger.info(f"[simple_activity_report_for_a_model] Report generated with {record_count} records.")
    except LookupError:
        logger.error(f"Model {model_name} in app {app_label} does not exist.")
        record_count = -1
        raise
    except Exception as ex:
        logger.exception("Error during report generation.")
        record_count = -1
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Execution time: {execution_time / 60:.2f} minutes.")
        return f"Exported {record_count} records in {execution_time / 60:.2f} minutes."
