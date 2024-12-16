from celery import shared_task


@shared_task(bind=True, time_limit=30 * 60, max_retries=2)
def task_execute_forwards(self, company_id:int):
    import time
    import logging

    from main.apps.account.models.company import Company
    from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
    from main.apps.hedge.services.forward_execution import ForwardExecutionService


    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.info(f"[task_execute_forwards] Running drawdown forwards for "
            f"company_id={company_id}")

        company = Company.objects.get(pk=company_id)
        if company.status != Company.CompanyStatus.ACTIVE:
            raise Exception(f"Company (ID:{company_id}) is not active.")

        logging.info(f"Pending Forward Command flow for company (ID={company_id}).")

        factory = CorPayExecutionServiceFactory()
        execution_service = factory.for_company(company)
        ForwardExecutionService(execution_service).update_forwards(company)

        logger.debug("[task_execute_forwards] Drawdown forward for a company task executed successfully!")
    except Exception as ex:
        logger.exception(f"[task_execute_forwards] Error executing drawdown forward for a company task: {ex}")
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[task_execute_forwards] Execution time for task_execute_forwards: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
