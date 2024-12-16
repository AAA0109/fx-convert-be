from celery import shared_task


@shared_task(bind=True, time_limit=30 * 60, max_retries=2)
def task_check_if_company_orders_are_done(self, company_id:int, retry_time:int = 15, timeout:int = 15):
    import datetime as dt
    import time
    import logging

    from hdlib.DateTime.Date import Date

    from main.apps.account.models.account import Account
    from main.apps.account.models.company import Company
    from main.apps.oems.services.order_service import OrderService

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.info(f"[task_check_if_company_orders_are_done] Running check orders are done for "
            f"company_id={company_id}")

        company = Company.objects.get(pk=company_id)
        if company.status != Company.CompanyStatus.ACTIVE:
            raise Exception(f"Company (ID:{company_id}) is not active.")

        timeout_delta = dt.timedelta(minutes=timeout)
        end_timestamp = Date.now().__add__(amount=timeout_delta).timestamp()

        logging.info(f"Start checking if company ({company.name}) orders are done.")
        order_service = OrderService()
        if Account.has_live_accounts(company=company):
            while not order_service.are_company_orders_done(company=company):
                if Date.now().timestamp() > end_timestamp:
                    raise Exception(f"Timeout for OMS to fill orders for {company.name}.")

                logger.debug(
                    f"Waiting for OMS to fill orders for {company.name}. "
                    f"Waiting {retry_time} seconds...")
                time.sleep(retry_time)
        logger.debug(f"Orders filled for {company.name}.")

        logger.debug("[task_check_if_company_orders_are_done] Check orders are done for company task executed successfully!")
    except Exception as ex:
        logger.exception(f"[task_check_if_company_orders_are_done] Check orders are done for company task: {ex}")
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[task_check_if_company_orders_are_done] Execution time for task_check_if_company_orders_are_done: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
