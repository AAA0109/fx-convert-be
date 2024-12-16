from celery import shared_task


@shared_task(bind=True, time_limit=30 * 60, max_retries=2)
def task_start_eod_flow_for_company(self, company_id:int):
    import time
    import logging

    from hdlib.DateTime.Date import Date

    from main.apps.account.models.company import Company
    from main.apps.hedge.services.eod_and_intra import EodAndIntraService

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.info(f"[task_start_eod_flow_for_company] Running Start EOD flow for "
            f"company_id={company_id}")

        company = Company.objects.get(pk=company_id)
        if company.status != Company.CompanyStatus.ACTIVE:
            raise Exception(f"Company (ID:{company_id}) is not active.")

        logging.info(f"Start eod flow for company (ID={company_id}).")

        ref_date = Date.now()
        eod_service = EodAndIntraService(ref_date=ref_date)
        eod_service.start_eod_flow_for_company(time=ref_date, company=company_id)

        logger.debug("[task_start_eod_flow_for_company] Start EOD flow for company task executed successfully!")
    except Exception as ex:
        logger.exception(f"[task_start_eod_flow_for_company] Error executing start EOD flow for company task: {ex}")
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[task_start_eod_flow_for_company] Execution time for task_start_eod_flow_for_company: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
