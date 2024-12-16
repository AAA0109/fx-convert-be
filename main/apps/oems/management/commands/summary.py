import logging

from datetime import date, datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from main.apps.currency.models import Currency
from main.apps.oems.backend.date_utils import parse_datetime, parse_date
from main.apps.account.models import Company

from main.apps.oems.services.reporting import generate_report

# ======================================

logger = logging.getLogger(__name__)

# ======================================

def parse_currency( x ):
    return Currency.get_currency(currency=x)

def parse_company( x ):
    return Company.objects.get(pk=int(x))

# ==========================

class TaskDefaultArgumentsMixin:
    def add_default_arguments(self, parser):
        pass

class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to submit a sample ticket"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

        # load existing ticket
        parser.add_argument('--start-date', type=parse_datetime, default=None)
        parser.add_argument('--end-date', type=parse_datetime, default=None)
        parser.add_argument('--rev-share', type=float, default=0.002) # 20bps
        # ====

        # actions
        parser.add_argument('--show', action='store_true')
        parser.add_argument('--send', action='store_true')
        parser.add_argument('--recips', nargs='+', default=None)

    def handle(self, *args, **options):
        generate_report(**options)

