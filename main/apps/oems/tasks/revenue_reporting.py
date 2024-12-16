import logging
import traceback

from celery import shared_task
from datetime import date, datetime

# ========

@shared_task(bind=True, time_limit=15 * 60, max_retries=2)
def task_revenue_report( self ):
    from main.apps.oems.services.reporting import generate_report
    generate_report()
