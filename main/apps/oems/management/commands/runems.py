import datetime as dt
import logging
import time

from django.core.management.base import BaseCommand

# ======

from main.apps.oems.backend.ems           import EmsBase
from main.apps.oems.backend.corpay_ems    import CorpayEms
from main.apps.oems.backend.rfq_ems       import RfqEms
from main.apps.oems.backend.strat_ex_ems  import StratExEms
from main.apps.oems.backend.rfq_mp_ems    import RfqMpEms
from main.apps.oems.backend.corpay_mp_ems import CorpayMpEms

# ======

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--ems-id", help="Required: EMS ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--ems-type', default='CORPAY')
        parser.add_argument('--log-level', default=None)
        parser.add_argument('--regen', action='store_true', default=False)
        parser.add_argument('--queue-name', default='global1')
        parser.add_argument('--batch-size', type=int, default=5)
        parser.add_argument('--timeout', type=float, default=0.5)

    def handle(self, *args, **options):

        ems_type = options['ems_type']

        # TODO: this should be a module load string
        if ems_type == 'CORPAY':
            obj = CorpayEms
        elif ems_type == 'RFQ':
            obj = RfqEms
        elif ems_type == 'CORPAY_MP':
            obj = CorpayMpEms
        elif ems_type == 'RFQ_MP':
            obj = RfqMpEms
        elif ems_type == 'STRAT_EX':
            obj = StratExEms
        else:
            raise ValueError
            obj = EmsBase

        # gslogging.disable(logging.INFO)

        print('running ems with options:', obj, options)

        server = obj( options['ems_id'], options['ems_type'],
                    log_level=options['log_level'], regen=options['regen'],
                    queue_name=options['queue_name'], batch_size=options['batch_size'], timeout=options['timeout'])
        server.run()

