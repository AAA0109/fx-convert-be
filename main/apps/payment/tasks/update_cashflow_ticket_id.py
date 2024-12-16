from celery import shared_task


@shared_task(time_limit=10 * 60, max_retries=2)
def update_cashflow_ticket_id_task(ticket_id:str=None, cashflow_id:str=None):
    import logging
    import time
    import uuid

    from main.apps.cashflow.models.cashflow import SingleCashFlow
    from main.apps.oems.models.ticket import Ticket

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    if not ticket_id:
        logger.error(f"[update_cashflow_ticket_id_task] ticket_id must be set!")
        return
    if not cashflow_id:
        logger.error(f"[update_cashflow_ticket_id_task] cashflow_id must be set!")
        return

    try:
        if cashflow_id:
            cashflow = SingleCashFlow.objects.get(cashflow_id=uuid.UUID(cashflow_id))
            cashflow.ticket_id = uuid.UUID(ticket_id)
            cashflow.save()
    except Exception as ex:
        logger.exception(f"[update_cashflow_ticket_id_task] Failed to update cashflow ticket id "
                         f"for ticket={ticket_id}: {ex}")
        # It's critical to raise the exception to ensure Celery is aware of the failure
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[update_cashflow_ticket_id_task] Execution time for "
                    f"update_cashflow_ticket_id_task: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
