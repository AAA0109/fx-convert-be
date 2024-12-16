import datetime as dt
import logging
import time
import yaml

from django.core.management.base import BaseCommand
from django.utils import module_loading
from django.conf import settings

from main.apps.oems.backend.run_container import RunContainer
from main.apps.oems.backend.utils         import load_yml

# ======

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--run-cfg", help="YAML Run Config", required=False)

class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--timeout', type=float, default=0.5)
        parser.add_argument('--log-level', default=None)
        parser.add_argument('--queue-name', default='global1')
        parser.add_argument('--batch-size', type=int, default=5)

    def handle(self, *args, **options):

        if options['run_cfg']:
            run_cfg = load_yml( options['run_cfg'] )
        else:
            if not hasattr(settings, 'OEMS_RUN_CFG'):
                raise ValueError('must provide yaml run file or use django settings to setup services')
            run_cfg = settings.OEMS_RUN_CFG

        container = RunContainer( timeout=options['timeout'] )

        for service_options in run_cfg:
            obj    = module_loading.import_string(service_options['service_class'])
            server = obj(
                    service_options['id'], service_options['type'],
                    log_level=service_options.get('log_level',options['log_level']),
                    queue_name=service_options.get('queue_name',options['queue_name']),
                    batch_size=service_options.get('batch_size',options['batch_size']),
                    child=True,
            )
            key = service_options['id'] + '|' + service_options['type']
            container.add_service( key, server )

        container.run()
        
