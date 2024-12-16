import traceback
from collections import defaultdict
from datetime import datetime, date
from functools import lru_cache

import pandas as pd
from django.conf import settings

from main.apps.account.models.company import Company
from main.apps.notification.services.email_service import send_email
from main.apps.oems.backend.db import init_db
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.backend.webhook import WEBHOOK_EVENTS
from main.apps.oems.models.ticket import Ticket as DjangoTicket


# =================

class MarkToMarket:

    def __init__(self, companies=None, dry_run=False):

        self._db = init_db()
        self.dry_run = dry_run
        self.tdy = date.today()
        self.tickets = self.load()

    def load(self):

        states = ','.join(map(self._db.pytype, INTERNAL_STATES.MTM_STATES))
        sql = f"select * from \"{Ticket.DJANGO_MODEL_NAME}\" where \"internal_state\" in ({states}) and \"instrument_type\" != 'spot' and \"value_date\" >= '{self.tdy.isoformat()}'"

        # TODO: filter spot

        try:
            ret = self._db.fetch_and_commit(sql, one_call=False)
        except:
            traceback.print_exc();
            print("SQL ERROR:", sql)
            ret = []

        return ret

    # ==========================================

    def mark_fwd(self, ticket):
        mtm = ticket.do_mark_to_market()
        return mtm

    def mark_ndf(self, ticket):
        mtm = ticket.do_mark_to_market()
        return mtm

    # ==========================================

    def dispatch_event(self, company, event_type, payload, user=None):
        if payload:
            # this won't work
            Webhook.dispatch_event(company, event_type, payload, user=user)

    @lru_cache
    def get_email_recipients(self, company):

        recipients = set()

        if settings.OEMS_EMAIL_RECIPIENTS:
            recipients.update(settings.OEMS_EMAIL_RECIPIENTS)
        else:
            company = Company.objects.get(pk=self.company_id)
            if company.account_owner:
                recipients.add(company.account_owner)
            if company.rep:
                recipients.add(company.rep)

        if recipients: return list(recipients)

    def send_market_to_market_email(self, company, recipients, table, title='MTM Statement', order_id=''):

        context = {
            'title': title,
            'company': company.name,
            'operation': '',
            'date': date.today().isoformat(),
            'order_id': order_id,
        }

        df = pd.DataFrame(table)

        send_email('mtm', context, df, recipients)

    def send_ticket_market_to_market(self, ticket, payload):

        if self.dry_run: return

        company = Company.objects.get(pk=ticket.company_id)
        recipients = self.get_email_recipients(company)

        if recipients:
            self.send_market_to_market_email(company, recipients, payload, title='Transaction MTM Statement',
                                             order_id=ticket.ticket_id)

        self.dispatch_event(company, WEBHOOK_EVENTS.TRADE_MTM, payload=payload)

    def send_mark_to_market(self, company_id, table, title='MTM Statement'):

        if self.dry_run: return

        company = Company.objects.get(pk=company_id)

        recipients = self.get_email_recipients(company)

        if recipients:
            self.send_market_to_market_email(company, recipients, table, title=title)

        self.dispatch_event(company, WEBHOOK_EVENTS.PORTFOLIO_MTM, payload=table)

    # ==========================================

    def update_ticket_mtm(self, ticket, payload):

        ticket.mark_to_market = payload.get('mark_to_market')
        ticket.last_mark_time = datetime.utcnow()
        ticket.mtm_info = payload
        if not self.dry_run: ticket.save()

        self.send_ticket_market_to_market(ticket, payload)

    def mark_to_market(self):

        by_company = defaultdict(list)

        # TODO: Not a great way to do this. better to load by company and parallelize
        for row in self.tickets:

            ticket = Ticket(**row)

            if ticket.instrument_type == DjangoTicket.InstrumentTypes.SPOT:
                continue

            if ticket.instrument_type == DjangoTicket.InstrumentTypes.FWD:
                table_row = self.mark_fwd(ticket)
                if table_row:
                    self.update_ticket_mtm(ticket, table_row)
                    by_company[ticket.company_id].append(table_row)
            elif ticket.instrument_type == DjangoTicket.InstrumentTypes.NDF:
                table_row = self.mark_ndf(ticket)
                if table_row:
                    self.update_ticket_mtm(ticket, table_row)
                    by_company[ticket.company_id].append(table_row)

        for company_id, table in by_company.items():
            empty_row = dict.fromkeys(table[0].keys())

            table.append(empty_row)

            total_row = empty_row.copy()
            total_row['market_name'] = 'TOTAL'
            # total_row['pnl_currency'] = table[0]['pnl_currency']
            total_row['mark_to_market'] = sum(
                row['mark_to_market'] for row in table if isinstance(row['mark_to_market'], float))
            table.append(empty_row)

            self.send_mark_to_market(company_id, table)


# ==============

"""
def create_fwd_to_ticket_celery_task(apps: Apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Convert Autopilot Forward to Ticket
    task, created = PeriodicTask.objects.get_or_create(
        name='Convert Autopilot Forward to Ticket',  # Human-readable name of the task
        defaults={
            'interval': None,
            'task': 'main.apps.hedge.tasks.convert_forward_to_ticket.convert_forward_to_ticket_with_strategy',
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': False,
        }
    )
"""
