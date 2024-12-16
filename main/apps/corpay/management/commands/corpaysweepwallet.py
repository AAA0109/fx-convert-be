import logging

from django.core.management import BaseCommand
from main.apps.corpay.services.fxbalance.sweep import CorPayFXBalanceSweepService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django command to sweep CorPay FXAccount balance"

    def add_arguments(self, parser):
        parser.add_argument("--company_id", type=int, nargs='?')

    def handle(self, *args, **options):
        company_id = None
        if options["company_id"] is not None:
            company_id = options["company_id"]
        service = CorPayFXBalanceSweepService()
        service.execute(company_id)
