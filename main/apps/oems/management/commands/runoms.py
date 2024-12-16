import datetime as dt
import logging
import time

from django.core.management.base import BaseCommand

# ======

from main.apps.oems.backend.oms import OmsBase

# ======

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--oms-id", help="Required: OMS ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--oms-type', default='CORPAY')
        parser.add_argument('--log-level', default=None)
        parser.add_argument('--regen', action='store_true', default=False)
        parser.add_argument('--queue-name', default='global1')
        parser.add_argument('--batch-size', type=int, default=5)
        parser.add_argument('--timeout', type=float, default=0.5)

    def handle(self, *args, **options):

        # TODO: check if already running
        
        # untyped for now
        obj = OmsBase

        print('running oms with options:', obj, options)

        server = obj( options['oms_id'], options['oms_type'],
                    log_level=options['log_level'], regen=options['regen'],
                    queue_name=options['queue_name'], batch_size=options['batch_size'], timeout=options['timeout'])
        server.run()
        
