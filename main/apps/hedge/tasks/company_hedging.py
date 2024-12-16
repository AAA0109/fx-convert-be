from celery import shared_task, group, chain


@shared_task(bind=True, time_limit=30 * 60, max_retries=2)
def task_hedging_for_a_company(self, company_id:int, retry_time:int = 15, timeout:int = 15):
    import time
    import logging

    from main.apps.account.models.company import Company

    from main.apps.hedge.tasks.drawdown_forwards import task_drawdown_forwards
    from main.apps.hedge.tasks.end_eod_flow_for_company import task_end_eod_flow_for_company
    from main.apps.hedge.tasks.execute_forwards import task_execute_forwards
    from main.apps.hedge.tasks.start_eod_flow_for_company import task_start_eod_flow_for_company
    from main.apps.oems.tasks.check_if_company_orders_are_done import task_check_if_company_orders_are_done

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.info(f"[task_hedging_for_a_company] Running hedging for "
            f"company_id={company_id}")

        company = Company.objects.get(pk=company_id)
        if company.status != Company.CompanyStatus.ACTIVE:
            raise Exception(f"Company (ID:{company_id}) is not active.")

        hedging_flows = chain(
            task_drawdown_forwards.si(company_id=company_id),
            task_execute_forwards.si(company_id=company_id),
            task_start_eod_flow_for_company.si(company_id=company_id),
            task_check_if_company_orders_are_done.si(company_id=company_id, retry_time=retry_time, timeout=timeout),
            task_end_eod_flow_for_company.si(company_id=company_id)
        )
        hedging_flows.apply_async()

        logger.debug("[task_hedging_for_a_company] Hedging for a company task excuted successfully!")
    except Exception as ex:
        logger.exception(f"[task_hedging_for_a_company] Error executing hedging for a company task: {ex}")
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[task_hedging_for_a_company] Execution time for task_hedging_for_a_company: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(time_limit=30 * 60, max_retries=2)
def task_hedging_for_all_companies(retry_time:int = 15, timeout:int = 15):
    import time
    import logging

    from django.db.models import Q

    from main.apps.account.models.company import Company

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.info(f"[task_hedging_for_all_companies] Running hedging for all companies")

        company_ids_to_hedge = Company.objects.filter(
            Q(broker_accounts__broker__name="IBKR")
            | Q(corpaysettings__isnull=False)
        ).values_list('id', flat=True)

        tasks = [task_hedging_for_a_company.si(company_id=company_id, retry_time=retry_time, timeout=timeout) for company_id in company_ids_to_hedge]
        group(*tasks).apply_async()
    except Exception as ex:
        logger.exception(f"[task_hedging_for_all_companies] Failed to initiate hedging all companies task")
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[task_hedging_for_all_companies] Execution time for "
                    f"task_hedging_for_all_companies: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
