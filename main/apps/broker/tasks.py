from celery import shared_task


@shared_task
def sync_broker_user_instruments_task(user_id):
    ...
