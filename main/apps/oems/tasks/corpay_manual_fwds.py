import logging
import traceback

from celery import shared_task

# ========

@shared_task(bind=True, time_limit=15 * 60, max_retries=2)
def task_check_corpay_manual_fwds( self, dry_run=False ):

    from main.apps.account.models import Company
    from main.apps.oems.services.backfill_corpay import backfill_forwards

    # filter only companies who are active on corpay
    for company in Company.objects.all():
        # check if valid for corpay
        try:
            backfill_forwards( company, dry_run=dry_run )
        except:
            traceback.print_exc()


@shared_task(bind=True, time_limit=15 * 60, max_retries=2)
def task_check_monex_manual_transactions( self, dry_run=False ):

    from main.apps.account.models import Company
    from main.apps.oems.services.backfill_monex import backfill_forwards, backfill_spot_orders

    # filter only companies who are active on monex
    for company in Company.objects.all():
        # check if valid for monex
        try:
            backfill_spot_orders( company, dry_run=dry_run )
        except:
            traceback.print_exc()


        try:
            backfill_forwards( company, dry_run=dry_run )
        except:
            traceback.print_exc()



