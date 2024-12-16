import csv
import uuid
from unittest import skip

from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.models.ticket import Ticket as DjangoTicket


@skip("Test script exclude from unit test")
def run():
    company = Company.objects.first()
    draft = False

    with open('/Users/hunter/work/hedgedesk_dashboard/main/apps/oems/scripts/load_tickets.csv') as f:

        header = None
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            print(row)

            from_ccy = Currency.get_currency(row['from_ccy'])
            to_ccy = Currency.get_currency(row['to_ccy'])
            market_name = FxPair.get_pair_from_currency(from_ccy, to_ccy).market

            all_in_rate = float(row['all_in_rate'])
            all_in_done = abs(float(row['all_in_done']))
            all_in_cntr_done = abs(float(row['all_in_cntr_done']))  # all_in_done * all_in_rate
            value_date = Date.from_int(int(row['value_date'].replace('-', '')))

            ticket = Ticket(
                transaction_id=uuid.uuid4(),
                company=company,
                sell_currency=from_ccy,
                buy_currency=to_ccy,
                market_name=market_name,
                side=row['side'],
                amount=all_in_done,
                lock_side=from_ccy,
                tenor='fwd',
                value_date=value_date,
                instrument_type=row['instrument_type'],
                draft=draft,
                time_in_force='1min',
                ticket_type='PAYMENT',
                action='execute',
                execution_strategy='market',
                trader='hunter',
                all_in_done=all_in_done,
                all_in_rate=all_in_rate,
                all_in_cntr_done=all_in_cntr_done,
                external_id=row['order_number']
            )

            for fld in DjangoTicket._meta.fields:
                name = fld.name
                if name in ('id', 'created', 'modified'): continue
                if not hasattr(ticket, name):
                    setattr(ticket, name, None)

            # ticket.send_confirm()

            mtm = ticket.mark_to_market()
            ticket.send_mark_to_market(payload=mtm)

            breakpoint()

            if False:
                ticket.save()
