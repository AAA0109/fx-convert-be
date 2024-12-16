from celery import shared_task, group


@shared_task(bind=True, time_limit=10 * 60, max_retries=2)
def convert_forward_to_ticket(self, strategy:str = None, draft_fwd_position_id:int = None):
    import logging
    import time

    from django.core.exceptions import ObjectDoesNotExist

    from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
    from main.apps.hedge.services.forward_to_ticket import ForwardToTicketFactory

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    try:
        logger.debug(
            f"[convert_forward_to_ticket] Convert forward to ticket "
            f"draft_fwd_id={draft_fwd_position_id} "
            f"with strategy: {strategy}")

        try:
            draft_fwd_position = DraftFxForwardPosition.objects.get(pk=draft_fwd_position_id)
        except ObjectDoesNotExist:
            logger.error(f"[convert_forward_to_ticket] Draft fx forward position with id {draft_fwd_position_id} does not exist.")
            return

        fwd_to_ticket = ForwardToTicketFactory()
        fwd_to_ticket.convert_forward_to_ticket(draft_fwd_position=draft_fwd_position, strategy=strategy)

        logger.debug(f"[convert_forward_to_ticket] Draft fx forward position {draft_fwd_position_id} converted successfully!")
    except Exception as ex:
        logger.exception(f"[convert_forward_to_ticket] Error converting forward to ticket task: {ex}")
        # Ensuring that the exception is logged with stack trace for better debugging
        # Reraise the exception to let Celery handle retries or failure logging
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[convert_forward_to_ticket] Execution time for convert_forward_to_ticket: {execution_time} seconds")
        return f"{execution_time / 60} minutes"


@shared_task(time_limit=10 * 60, max_retries=2)
def convert_forward_to_ticket_with_strategy(strategy=None):
    import logging
    import time
    from main.apps.hedge.services.forward_to_ticket import ForwardToTicketFactory

    logger = logging.getLogger("root")

    # Start timing
    start_time = time.time()

    if not strategy:
        logger.error(f"[convert_forward_to_ticket_with_strategy] strategy must be set!")
        return

    if not ForwardToTicketFactory().strategy_exist(strategy=strategy):
        logger.error(f"[convert_forward_to_ticket_with_strategy] {strategy} strategy doesn't exist!")
        return

    try:
        draft_fwd_positions = ForwardToTicketFactory.populate_forward_to_convert(strategy=strategy)

        tasks = [convert_forward_to_ticket.s(strategy=strategy, draft_fwd_position_id=draft_fwd_position.pk)
                 for draft_fwd_position in draft_fwd_positions]
        group(*tasks).apply_async()
    except Exception as ex:
        logger.exception(f"[convert_forward_to_ticket_with_strategy] Failed to initiate forward to ticket converter "
                         f"with startegy={strategy}: {ex}")
        # It's critical to raise the exception to ensure Celery is aware of the failure
        raise
    finally:
        # End timing
        end_time = time.time()
        # Calculate the total execution time
        execution_time = end_time - start_time
        # Log or print the execution time
        logger.debug(f"[convert_forward_to_ticket_with_strategy] Execution time for "
                    f"convert_forward_to_ticket_with_strategy: {execution_time} seconds")
        return f"{execution_time / 60} minutes"
