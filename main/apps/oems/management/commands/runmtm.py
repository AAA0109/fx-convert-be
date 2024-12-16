
import logging
import time

from django.core.management.base import BaseCommand

from main.apps.oems.backend.mtm import MarkToMarket

# ======

logger = logging.getLogger(__name__)

class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        ...

class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--company-ids', nargs='+', default=None)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):

        print('running mtm server with options:', options)

        server = MarkToMarket(companies=options['company_ids'], dry_run=options['dry_run'])
        server.mark_to_market()

        
