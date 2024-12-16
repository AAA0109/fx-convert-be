import logging
import uuid

from datetime import date, datetime

from django.core.management.base import BaseCommand

from main.apps.oems.services.connector.oems import OEMSEngineAPIConnector
from main.apps.oems.models.ticket import Ticket

from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.currency.models import Currency
from main.apps.oems.backend.date_utils import parse_datetime, parse_date
from main.apps.account.models import Company

def parse_currency( x ):
    return Currency.get_currency(currency=x)

def parse_company( x ):
    return Company.objects.get(pk=int(x))

logger = logging.getLogger(__name__)

# ======================================

def infer_instrument( market_name, value_date ):
    pass


# ======================================

class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to submit a sample ticket"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

        # load existing ticket
        parser.add_argument('--existing-ticket-id', default=None)

        # ====

        parser.add_argument('--company-id', type=parse_company, required=False)
        parser.add_argument('--company-name', default=None)
        parser.add_argument('--buy-currency', type=parse_currency, required=False)
        parser.add_argument('--sell-currency', type=parse_currency, required=False)
        parser.add_argument('--lock-side', type=parse_currency, required=False)
        parser.add_argument('--value-date', type=parse_date, default=date.today())
        parser.add_argument('--ticket-id', default=None)
        parser.add_argument('--order-number', default=None, required=False)
        parser.add_argument('--all-in-done', type=float, required=False)
        parser.add_argument('--all-in-cntr-done', type=float, required=False)
        parser.add_argument('--broker', default='CORPAY')
        parser.add_argument('--rate', type=float)

        # optional
        parser.add_argument('--customer-id', default=None)
        parser.add_argument('--cashflow-id', default=None)
        parser.add_argument('--transaction-id', default=None)
        parser.add_argument('--transaction-group', default=None)
        parser.add_argument('--trader', default='brian')
        parser.add_argument('--draft', action='store_true', default=False)
        parser.add_argument('--with-care', action='store_true', default=False)
        parser.add_argument('--time-in-force', choices=Ticket.TimeInForces.values, default=Ticket.TimeInForces._GTC)
        parser.add_argument('--tenor', choices=Ticket.Tenors.values, default=None)
        parser.add_argument('--date-conversion', choices=Ticket.DateConvs.values, default=Ticket.DateConvs.MODF)
        parser.add_argument('--action', default='execute')
        parser.add_argument('--execution-strategy', choices=Ticket.ExecutionStrategies.values, default='market')
        parser.add_argument('--instrument-type', choices=Ticket.InstrumentTypes.values, default=None)

        # actions
        parser.add_argument('--send', action='store_true')
        parser.add_argument('--save', action='store_true')
        parser.add_argument('--recips', nargs='+', default=None)

    def handle(self, *args, **options):

        etid = options.get('existing_ticket_id')

        if etid:
            ticket = Ticket.objects.get(ticket_id=etid)
        else:
            for fld in ('company_id','buy_currency','sell_currency','lock_side','order_number','all_in_done','all_in_cntr_done'):
                if not options[fld]: raise ValueError

            tid = options['ticket_id'] or uuid.uuid4()

            fxpair, side = determine_rate_side( options['sell_currency'], options['buy_currency'] )
            market_name = fxpair.market

            if side == 'Sell':
                all_in_rate = round(options['all_in_cntr_done']/options['all_in_done'],4)
            else:
                all_in_rate = round(options['all_in_done']/options['all_in_cntr_done'],4)

            instrument_type = options['instrument_type'] or infer_instrument( market_name, options['value_date'] )

            ticket = Ticket(
                ticket_id=tid,
                company=options['company_id'],
                amount=options['all_in_done'] if options['lock_side'] == options['sell_currency'] else options['all_in_cntr_done'],
                sell_currency=options['sell_currency'],
                buy_currency=options['buy_currency'],
                market_name=market_name,
                side=side,
                lock_side=options['lock_side'],
                tenor=options['tenor'],
                value_date=options['value_date'],
                instrument_type=instrument_type,
                time_in_force=options['time_in_force'],
                ticket_type='PAYMENT',
                rate=options['rate'],
                action=options['action'],
                execution_strategy=options['execution_strategy'],
                trader=options['trader'],
                all_in_done = options['all_in_done'],
                all_in_rate = all_in_rate,
                all_in_cntr_done = options['all_in_cntr_done'],
                broker_id=options['order_number'],
                broker=options['broker'],
                customer_id=options['customer_id'],
                cashflow_id=options['cashflow_id'],
                transaction_id=options['transaction_id'],
                transaction_group=options['transaction_group'],
                draft=options['draft'],
                with_care=options['with_care'],
            )

            if options['save']:
                ticket.save()

        if options['send']:
            ticket.send_confirm(recipients=options['recips'], company_name=options['company_name'])


