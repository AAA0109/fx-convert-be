from datetime import date, datetime
import logging
import time
import getpass
import uuid

from django.core.management.base import BaseCommand
from django.conf import settings

# ======

from main.apps.currency.models.currency import Currency
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.services.trading import trading_provider
from main.apps.oems.backend.date_utils import parse_datetime, parse_date

# ======

logger = logging.getLogger(__name__)

# ======

def parse_currency( x ):
    return Currency.get_currency(currency=x)

# ======

class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        ...


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           required=True)

        # ======

        getapi = subparsers.add_parser("execute-rfq")
        getapi.add_argument('--ticket-id', default=None)
        getapi.add_argument('--amount', type=float, default=None)
        getapi.add_argument('--settle-account-id', default=None)
        getapi.add_argument('--beneficiary-id', default=None)
        getapi.add_argument('--beneficiaries', type=str, default=None)
        getapi.add_argument('--settlement-info', type=str, default=None)

        # ======

        createapi = subparsers.add_parser("rfq")
        createapi.add_argument('--buy-currency', type=parse_currency, required=True)
        createapi.add_argument('--sell-currency', type=parse_currency, required=True)
        createapi.add_argument('--lock-side', type=parse_currency, required=True)
        createapi.add_argument('--value-date', type=parse_date, default=date.today())
        createapi.add_argument('--amount', type=float, required=True)
        createapi.add_argument('--ticket-id', default=None)
        createapi.add_argument('--settle-account-id', default=None)
        createapi.add_argument('--beneficiary-id', default=None)
        createapi.add_argument('--customer-id', default=None)
        createapi.add_argument('--cashflow-id', default=None)
        createapi.add_argument('--transaction-id', default=None)
        createapi.add_argument('--transaction-group', default=None)
        createapi.add_argument('--draft', action='store_true', default=False)
        createapi.add_argument('--with-care', action='store_true', default=False)
        createapi.add_argument('--time-in-force', choices=Ticket.TimeInForces.values, default=Ticket.TimeInForces._10SEC)
        createapi.add_argument('--tenor', choices=Ticket.Tenors.choices, default=None)
        createapi.add_argument('--date-conversion', choices=Ticket.DateConvs.values, default=Ticket.DateConvs.MODF)
        createapi.add_argument('--action', default='rfq')
        createapi.add_argument('--execution-strategy', choices=Ticket.ExecutionStrategies.values, default='market')
        createapi.add_argument('--beneficiaries', type=str, default=None)
        createapi.add_argument('--settlement-info', type=str, default=None)

        # ======

        cancelapi = subparsers.add_parser("execute")
        cancelapi.add_argument('--buy-currency', type=parse_currency, required=True)
        cancelapi.add_argument('--sell-currency', type=parse_currency, required=True)
        cancelapi.add_argument('--lock-side', type=parse_currency, required=True)
        cancelapi.add_argument('--value-date', type=parse_date, default=date.today())
        cancelapi.add_argument('--amount', type=float, required=True)
        cancelapi.add_argument('--settle-account-id', default=None)
        cancelapi.add_argument('--beneficiary-id', default=None)
        cancelapi.add_argument('--customer-id', default=None)
        cancelapi.add_argument('--cashflow-id', default=None)
        cancelapi.add_argument('--transaction-id', default=None)
        cancelapi.add_argument('--transaction-group', default=None)
        cancelapi.add_argument('--draft', action='store_true', default=False)
        cancelapi.add_argument('--with-care', action='store_true', default=False)
        cancelapi.add_argument('--time-in-force', choices=Ticket.TimeInForces.values, default=Ticket.TimeInForces._GTC)
        cancelapi.add_argument('--tenor', choices=Ticket.Tenors.values, default=None)
        cancelapi.add_argument('--date-conversion', choices=Ticket.DateConvs.values, default=Ticket.DateConvs.MODF)
        cancelapi.add_argument('--action', default='execute')
        cancelapi.add_argument('--execution-strategy', choices=Ticket.ExecutionStrategies.values, default='market')
        cancelapi.add_argument('--start-date', type=parse_datetime, default=None)
        cancelapi.add_argument('--end-date', type=parse_datetime, default=None)
        cancelapi.add_argument('--beneficiaries', type=str, default=None)
        cancelapi.add_argument('--settlement-info', type=str, default=None)

        # ======

    def handle(self, *args, **options):

        subcmd = options['subcommand']

        from rest_framework.authtoken.models import Token
        token = Token.objects.get(key=settings.DASHBOARD_API_TOKEN)
        user = token.user

        if subcmd == 'execute':
            ret = trading_provider.execute( user, options )
            print( ret )
        elif subcmd == 'rfq':
            ret = trading_provider.rfq( user, options )
            print( ret )
        elif subcmd == 'execute_rfq':
            ret = trading_provider.execute_rfq( user, options )
        else:
            raise ValueError



