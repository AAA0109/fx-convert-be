from celery import shared_task, group


@shared_task(time_limit=10 * 60, max_retries=2)
def cancel_single_ticket_task(ticket_id:str=None):
    import logging
    import time

    from main.apps.oems.services.trading import trading_provider


    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    if not ticket_id:
        logger.error(f"[cancel_single_ticket_task] ticket_id must be set!")
        return

    try:
        response = trading_provider.req_cancel(request={'ticket_id':ticket_id})
        if response.status_code != 202:
            raise Exception(response.data['message'])
        logger.info(f"[cancel_single_ticket_task] Ticket canceled successfully. Poll ID: {response.data['poll-id']}")
    except Exception as ex:
        logger.error(f"[cancel_single_ticket_task] Failed to cancel ticket"
                         f"for ticket={ticket_id}: {ex}", exc_info=True)
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[cancel_single_ticket_task] Execution time for "
                    f"cancel_single_ticket_task: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(time_limit=10 * 60, max_retries=2)
def bulk_ticket_cancel_task(payment_id:str=None):
    import logging
    import time

    from main.apps.payment.models.payment import Payment

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    if not payment_id:
        logger.error(f"[bulk_ticket_cancel_task] payment_id must be set!")
        return

    try:
        payment = Payment.objects.get(pk=payment_id)
        tasks = []
        for cashflow in payment.related_cashflows:
            if cashflow.ticket_id:
                tasks.append(cancel_single_ticket_task.si(ticket_id=cashflow.ticket_id.__str__()))

        if len(tasks) > 0:
            group(*tasks).apply_async()
        logger.info(f"[bulk_ticket_cancel_task] Ticket bulk canceled executed successfully")
    except Exception as ex:
        logger.error(f"[bulk_ticket_cancel_task] Failed to bulk cancel ticket"
                         f"for payment_id={payment_id}: {ex}", exc_info=True)
    finally:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[bulk_ticket_cancel_task] Execution time for "
                    f"bulk_ticket_cancel_task: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
