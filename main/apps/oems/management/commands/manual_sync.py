import logging
import uuid
from datetime import date, datetime, timedelta

import pytz
from django.core.management.base import BaseCommand

from main.apps.account.models import Company
from main.apps.oems.services import backfill_corpay
from main.apps.oems.services import backfill_monex

# ========


def parse_company(x):
    return Company.objects.get(pk=int(x))


logger = logging.getLogger(__name__)

logging.disable(logging.DEBUG)


# =========


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to backfill tickets from corpay"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--company-id', type=parse_company, required=False)
        parser.add_argument('--all-companies', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--show', action='store_true')
        parser.add_argument('--order-number', default=None)
        parser.add_argument('--forward-id', default=None)
        parser.add_argument('--fwd-sync', action='store_true')
        parser.add_argument('--spot-sync', action='store_true')
        parser.add_argument('--confirm-sync', action='store_true')
        parser.add_argument('--list-companies', action='store_true')
        parser.add_argument('--corpay', action='store_true', default=False)
        parser.add_argument('--monex', action='store_true', default=False)

    # =======

    def handle(self, *args, **options):

        company = options['company_id']
        all_companies = options['all_companies']
        do_fwds = options['fwd_sync']
        do_spot = options['spot_sync']
        sync_confirms = options['confirm_sync']
        dry_run = options['dry_run']

        if options['list_companies']:
            for company in Company.objects.all():
                print(company.name, company.pk)
            raise SystemExit

        if all_companies:
            for company in Company.objects.all():
                if options['corpay']:
                    if do_fwds:
                        backfill_corpay.backfill_forwards(
                            company, dry_run=dry_run)
                if options['monex']:
                    if do_spot:
                        backfill_monex.backfill_spot_orders(
                            company, dry_run=dry_run)
                    if do_fwds:
                        backfill_monex.backfill_forwards(
                            company, dry_run=dry_run)
        elif do_fwds and company:
            if options['corpay']:
                backfill_corpay.backfill_forwards(company, dry_run=dry_run)
            if options['monex']:
                backfill_monex.backfill_spot_orders(company, dry_run=dry_run)
                backfill_monex.backfill_forwards(company, dry_run=dry_run)
        elif company:
            if options['order_number']:
                if options['corpay']:
                    raise
                    backfill_corpay.backfill_spot_order(
                        options['order_number'], company, dry_run=dry_run)
                if options['monex']:
                    if do_spot:
                        backfill_monex.backfill_spot_order(
                            company=company, order_number=options['order_number'], dry_run=dry_run)
                    if do_fwds:
                        backfill_monex.backfill_forwards(
                            company=company, order_number=options['order_number'], dry_run=dry_run)

            elif options['forward_id']:
                if options['corpay']:
                    backfill_corpay.backfill_forward(
                        company, options['forward_id'], dry_run=dry_run)
                if options['monex']:
                    backfill_monex.backfill_forward(
                        company, options['forward_id'], dry_run=dry_run)
        elif sync_confirms:
            ...
        else:
            raise ValueError
