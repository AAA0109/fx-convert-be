import copy
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from main.apps.dataprovider.models.collector_config import CollectorConfig
from main.apps.dataprovider.services.collectors.runner import CollectorRunner

# ======

# ======

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to run collector."

    def add_arguments(self, parser):
        parser.add_argument('--config-ids', nargs='+', default=None, help='Comma-separated list of collector configuration IDs')
        parser.add_argument('--log-level', default=None)

    def handle(self, *args, **options):
        if options['config_ids']:
            config_ids = list(map(int, options['config_ids']))
            active_configs = CollectorConfig.objects.filter(id__in=config_ids, active=True)
        else:
            active_configs = CollectorConfig.objects.filter(active=True)

        if not active_configs.exists():
            logging.error('No active collector configurations found.')
            return

        collectors = []
        for config in active_configs:
            collector_class = import_string(config.collector)
            collector_kwargs = copy.deepcopy(config.kwargs)
            collector_kwargs["collector_nm"] = f'{settings.APP_ENVIRONMENT}1'

            storage_config = config.storage_config
            collector_kwargs['writer'] = import_string(
                storage_config.writer) if storage_config.writer is not None else None
            collector_kwargs['publisher'] = import_string(
                storage_config.publisher) if storage_config.publisher is not None else None
            collector_kwargs['cache'] = import_string(
                storage_config.cache) if storage_config.cache is not None else None

            collector = collector_class(**collector_kwargs)
            collectors.append(collector)

        if not collectors: raise ValueError
        runner = CollectorRunner(*collectors)
        runner.run_forever()
