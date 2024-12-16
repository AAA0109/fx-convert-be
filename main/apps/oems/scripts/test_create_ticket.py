from unittest import skip

from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.backend.xover import enqueue


@skip("Test script exclude from unit test")
def run():
    draft = False
    company = Company.objects.get(pk=34)
    from_ccy = Currency.get_currency('USD')
    to_ccy = Currency.get_currency('INR')
    market_name = FxPair.get_pair_from_currency(from_ccy, to_ccy).market

    """
    all_in_rate = 82.419847
    all_in_done = 10000.0
    all_in_cntr_done = 824200 # all_in_done * all_in_rate
    value_date = Date.from_int(20240430)
    fixing_date = Date.from_int(20240426)
    ref_date = Date.from_int(20240405)
    """

    all_in_rate = 83.4028
    all_in_cntr_done = 2_000_000  # all_in_done * all_in_rate
    all_in_done = round(all_in_cntr_done / all_in_rate, 2)
    spot_rate = 83.3775
    fwd_points = round(all_in_rate - spot_rate, 9)
    value_date = Date.from_int(20240430)
    fixing_date = Date.from_int(20240426)
    transaction_time = '2024-04-12T04:11:04.002417'

    ticket = Ticket(
        transaction_id="06cc0758-500b-45a3-8e7d-032de2548d9b",
        company=company,
        sell_currency=from_ccy,
        buy_currency=to_ccy,
        market_name=market_name,
        side='sell',
        amount=all_in_cntr_done,
        lock_side=to_ccy,
        tenor='fwd',
        value_date=value_date,
        fixing_date=fixing_date,
        instrument_type='ndf',
        draft=draft,
        time_in_force='1min',
        ticket_type='PAYMENT',
        action='execute',
        execution_strategy='market',
        trader='hunter',
        all_in_done=all_in_done,
        all_in_rate=all_in_rate,
        transaction_time=transaction_time,
        all_in_cntr_done=all_in_cntr_done,
        spot_rate=spot_rate,
        fwd_points=fwd_points,
    )

    # mtm = ticket.mark_to_market( pnl_currency='USD', fwd_rate=None, ref_date=ref_date)
    # ref_date = Date.from_int(20240326)
    # fixing = ticket.mark_to_market( pnl_currency='USD', fwd_rate=83.3559, spot_rate=83.3559, ref_date=ref_date)

    recips = ['hunter@pangea.io']

    # ticket.send_email_confirm(['hunter@pangea.io']) # ,'abhijit@xflowpay.com','ashwin@xflowpay.com','matt@pangea.io'])

    cur_fwd_rate = 83.4655
    cur_spot_rate = 83.4422
    ref_date = Date.today()

    fixing = ticket.mark_to_market(pnl_currency='USD', fwd_rate=cur_fwd_rate, disc=1.0, spot_rate=cur_spot_rate,
                                   ref_date=ref_date)
    ticket.send_email_mtm(payload=fixing, recipients=recips)

    if False:
        ticket.save()

    if False:
        ret = enqueue('api2oms_dev', ticket.export(), uid=ticket.id, action='CREATE', source='TEST_SCRIPT')
        print(ret)

    return ticket
