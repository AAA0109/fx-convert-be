import datetime as dt
import logging
import time
import getpass
import uuid

from django.core.management.base import BaseCommand
from django.conf import settings

# ======

# from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.models.ticket import Ticket

# ======

logger = logging.getLogger(__name__)

class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument('--env', default=settings.APP_ENVIRONMENT)
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           required=True)

        getapi = subparsers.add_parser("list")
        getapi.add_argument('--id', type=int, default=None)
        getapi.add_argument('--ticket-id', default=None)

        createapi = subparsers.add_parser("create")
        createapi.add_argument('--draft', action='store_true', default=False)
        createapi.add_argument('--time-in-force', choices=Ticket.TimeInForces, default='1min')
        createapi.add_argument('--company', type=int, default=25)
        createapi.add_argument('--from-ccy', default='USD')
        createapi.add_argument('--to-ccy', default='EUR')
        createapi.add_argument('--amount', type=float, default=1000.0)
        createapi.add_argument('--tenor', choices=Ticket.Tenors, default='spot')
        createapi.add_argument('--lock-side', default=None)
        createapi.add_argument('--action', choices=Ticket.Actions, default='rfq')
        createapi.add_argument('--exec-strat', choices=Ticket.ExecutionStrategies, default='market')
        createapi.add_argument('--trader', default=getpass.getuser())
        createapi.add_argument('--send', action='store_true', default=False)
        createapi.add_argument('--poll', action='store_true', default=False)

        cancelapi = subparsers.add_parser("cancel")
        cancelapi.add_argument('--id', type=int, default=None, required=True)
        cancelapi.add_argument('--send', action='store_true', default=False)
        cancelapi.add_argument('--poll', action='store_true', default=False)

        activeapi = subparsers.add_parser("activate")
        activeapi.add_argument('--id', type=int, default=None, required=True)
        activeapi.add_argument('--send', action='store_true', default=False)
        activeapi.add_argument('--poll', action='store_true', default=False)

        pauseapi = subparsers.add_parser("pause")
        pauseapi.add_argument('--id', type=int, default=None, required=True)
        pauseapi.add_argument('--send', action='store_true', default=False)
        pauseapi.add_argument('--poll', action='store_true', default=False)

        resumeapi = subparsers.add_parser("resume")
        resumeapi.add_argument('--id', type=int, default=None, required=True)
        resumeapi.add_argument('--send', action='store_true', default=False)
        resumeapi.add_argument('--poll', action='store_true', default=False)

        modapi = subparsers.add_parser("modify")
        modapi.add_argument('--id', type=int, default=None, required=True)
        modapi.add_argument('--send', action='store_true', default=False)
        modapi.add_argument('--poll', action='store_true', default=False)

        delapi = subparsers.add_parser("delete")
        delapi.add_argument('--id', type=int, default=None, required=True)
        delapi.add_argument('--send', action='store_true', default=False)
        delapi.add_argument('--poll', action='store_true', default=False)

        exrfq = subparsers.add_parser("execute-rfq")
        exrfq.add_argument('--id', type=int, default=None, required=True)
        exrfq.add_argument('--send', action='store_true', default=False)
        exrfq.add_argument('--poll', action='store_true', default=False)

    def handle(self, *args, **options):

        subcmd = options['subcommand']

        if subcmd == 'list':
            print( options['ticket_id'] )
            if options['ticket_id']:
                ret = Ticket.objects.filter(ticket_id=options['ticket_id']).first()
            elif options['id']:
                ret = Ticket.objects.filter(pk=options['id']).first()
            else:
                ret = None
            if ret:
              ret.print()
        elif subcmd == 'create':
            from hdlib.DateTime.Date import Date

            from main.apps.account.models import Company
            from main.apps.currency.models import Currency
            from main.apps.currency.models.fxpair import FxPair
            from main.apps.oems.backend.xover import init_db, enqueue
            from main.apps.oems.backend.states import INTERNAL_STATES, OMS_API_ACTIONS
            from main.apps.oems.backend.utils import sleep_for

            company = Company.objects.filter(pk=options['company']).first()
            from_ccy = Currency.get_currency(options['from_ccy'])
            to_ccy = Currency.get_currency(options['to_ccy'])
            market_name = FxPair.get_pair_from_currency(from_ccy, to_ccy).market

            ticket = Ticket._create(
                transaction_id=uuid.uuid4(),
                company=company,
                from_currency=from_ccy,
                to_currency=to_ccy,
                amount=options['amount'],
                lock_side=Currency.get_currency(options['lock_side']) if options['lock_side'] else from_ccy,
                tenor=options['tenor'],
                value_date=Date.now() if options['tenor'] == 'spot' else None,
                draft=options['draft'],
                time_in_force=options['time_in_force'],
                ticket_type='PAYMENT',
                action=options['action'], # defaulted
                execution_strategy=options['exec_strat'], # defaulted
                trader=options['trader'], # provided ?
                market_name=market_name,
            )

            if options['send']:
                ticket.save()
                ret = enqueue(f'api2oms_{options["env"]}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.CREATE, source='TEST_SCRIPT')
                print('INFO: created ticket id:', ticket.id)
                if options['poll']:
                    n = 0
                    while n < 100:
                        ticket.refresh_from_db()
                        if ticket.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
                            break
                        sleep_for(1.1)
                        n += 1
                    print('INFO: ticket is in state after polling', ticket.internal_state)
                    if ticket.internal_state == INTERNAL_STATES.RFQ_DONE:
                        if input(f'RFQ COMPLETE: do you want to execute this quote: {ticket.external_quote}? ').lower() == 'y':
                            ticket.action = 'execute'
                            ticket.destination = 'CORPAY'
                            ticket.save()
                            ret = enqueue(f'api2oms_{options["env"]}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.EXECUTE_RFQ, source='TEST_SCRIPT')
                            if options['poll']:
                                n = 0
                                while n < 10:
                                    ticket.refresh_from_db()
                                    # this should not be RFQ_DONE
                                    if ticket.internal_state != INTERNAL_STATES.RFQ_DONE and ticket.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
                                        break
                                    sleep_for(1.1)
                                    n += 1
                                print('INFO: ticket is in state after polling', ticket.internal_state)
                                ticket.print()
        elif sub_cmd == 'execute_rfq':
            ticket = Ticket.objects.filter(pk=options['id']).first()
            if ticket.internal_state == INTERNAL_STATES.RFQ_DONE:
                if options['send']:
                    ticket.action = 'execute'
                    ticket.destination = 'CORPAY'
                    ticket.save()
                    ret = enqueue(f'api2oms_{options["env"]}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.EXECUTE_RFQ, source='TEST_SCRIPT')
                    if options['poll']:
                        n = 0
                        while n < 100:
                            ticket.refresh_from_db()
                            if ticket.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
                                break
                            sleep_for(1.1)
                            n += 1
                        print('INFO: ticket is in state after polling', ticket.internal_state)
        elif sub_cmd in ('cancel','activate','pause','resume'):
            ticket = Ticket.objects.filter(pk=options['id']).first()
            if ticket.oms_owner:
                if options['send']:
                    ret = enqueue(f'api2oms_{options["env"]}_{ticket.oms_owner}', { 'id': ticket.id }, uid=ticket.id, action=getattr(OMS_API_ACTIONS, sub_cmd.upper()), source='TEST_SCRIPT')
            else:
                print('INFO: ticket cannot receive actions until actively assigned to an oms')
        elif sub_cmd == 'modify':
            pass
        elif sub_cmd == 'delete':
            pass


