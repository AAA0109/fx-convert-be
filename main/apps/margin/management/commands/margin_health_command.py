import logging

from django.core.management.base import BaseCommand

from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.margin.services.margin_health import MarginHealthService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check a company's margin health"

    def add_arguments(self, parser):
        parser.add_argument('--company_id', type=int)
        parser.add_argument('--deposit_required_level', type=float, default=0.5)

    @decorator_to_post_exception_message_on_slack()
    def handle(self, *args, **options):
        try:
            margin_health = MarginHealthService(company_id=options['company_id'],
                                                deposit_required_level=options['deposit_required_level'])
            margin_health.execute()
            logging.info("Command executed successfully!")


        except Exception as e:
            logging.error(e)
            raise Exception(e)
