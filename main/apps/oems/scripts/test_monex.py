from datetime import date, timedelta
from unittest import skip

from main.apps.account.models import Company
from main.apps.monex.services.monex import MonexApi


@skip("Test script exclude from unit test")
def run(*args):
    api = MonexApi.init()

    # tested
    # ret = api.login()
    # api.logout()

    # tested
    ccy_map = api.get_currencies(None)

    # ret2 = api.get_currency_pairs( None )
    # ret3 = api.get_holding_accounts( None )

    # tested
    # ret = api.get_all_forwards( None )
    # ret2 = api.get_all_spot_orders( None )

    # tested
    # ret = api.get_historical_rates( None, 'USDJPY', date.today(), date.today()+timedelta(days=1) )

    # tested
    # order_details = api.get_spot_settlement_info( 'RCBSSSNHNLZY7Z5M' )

    from_ccy = 'USD'
    to_ccy = 'EUR'

    company = Company.objects.get(pk=13)

    if False:
        vd = date.today() + timedelta(days=21)
        spot = False
    # response = api.get_forward_rate( company, from_ccy, to_ccy, from_ccy, 1000.0, vd )
    # {'data': {'firstQuote': True, 'quoteTimerSecs': 30, 'quotedData': {'valueDate': '2024-07-23T20:00:00-04:00', 'symbolCcy1Id': 42, 'symbolCcy2Id': 1, 'rate': '1.0907', 'amountCcyId': 42, 'amount': '916.84', 'costCcyId': 1, 'cost': 1000, 'margin': 4, 'marginCcyId': 1, 'marginAmount': 40, 'exchangeRateIsLowerThanMarketRate': False}}}
    else:
        vd = date.today() + timedelta(days=2)
        spot = True
    # tested
    # value_date = date.today() + timedelta(days=20)
    # offset = api.lookup_value_date_offset( company, from_ccy, to_ccy, value_date )

    response = api.get_quick_rate(company, from_ccy, to_ccy, from_ccy, 1000.0, spot=spot, value_date=vd)
    # {'firstQuote': True, 'quotedData': {'rates': [{'pairCCY1': 42, 'pairCCY2': 1, 'isBuy': False, 'displayRate': '1.0897', 'markupPercentage': '', 'realRate': 0.9176837661741765, 'amount': '917.68', 'cost': 1000, 'amountCCY': 42, 'costCCY': 1, 'exchangeRateIsLowerThanMarketRate': False}], 'pays': [], 'totals': [], 'err': False}, 'quoteTimerSecs': 30, 'wid': '79CDA8286B31A52667C9C09C107A15FA', 'tradeDone': False, 'workflow': 'payment'}

    response2 = api.execute_payment_rate(company, response['wid'], workflow=response['workflow'])
    response3 = api.complete_payment_rate(company, response['wid'], workflow=response['workflow'])

    print(response)
    print(response2)
    print(response3)

    breakpoint()
