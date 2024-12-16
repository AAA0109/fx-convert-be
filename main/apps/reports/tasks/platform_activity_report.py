from celery import shared_task


@shared_task(bind=True, time_limit=10 * 60, max_retries=2)
def task_to_generate_platform_activity_report(
    self,
    frequency: str,
    report_output_type: str,
):
    import logging
    import time

    logger = logging.getLogger("root")
    start_time = time.time()

    try:
        logger.info(f"[task_to_generate_platform_activity_report] "
                    f"generating report for frequency={frequency}, format={report_output_type}")

        from main.apps.reports.services.platform.activity import PlatformActivityReportingService
        PlatformActivityReportingService(
            report_name=f"{frequency.upper()} - Platform Activity Report",
            frequency=PlatformActivityReportingService.Frequency[frequency.upper()],
            report_output_type=PlatformActivityReportingService.ReportType[report_output_type.upper()]
        ).generate_report()
        logger.info(f"[task_to_generate_platform_activity_report] "
                    f"generated report for frequency={frequency}, format={report_output_type}")

    except Exception as ex:
        logger.exception(f"[task_to_generate_platform_activity_report] "
                         f"Error generating report for frequency={frequency}, format={report_output_type}",
                         exc_info=ex
                         )
        raise
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Execution time: {execution_time / 60:.2f} minutes.")
        return f"Execution time: {execution_time / 60:.2f} minutes."
