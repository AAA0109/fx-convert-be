import os, sys
from hdlib.DateTime.Date import Date
# from scripts.lib.only_local import only_allow_local


"""
Example Script for marking to market a cashflow using forwards
"""


def run():

    from main.apps.marketdata.services.initial_marketdata import convert_currency_amount, get_initial_market_state, get_recent_fwd_points, get_recent_fwd_outright, get_recent_spot_rate
    from main.apps.currency.models import FxPair
    from main.apps.currency.models.currency import Currency

    from_ccy = Currency.get_currency('USD')
    to_ccy = Currency.get_currency('JPY')
    lock_side = from_ccy
    amount = 1_000_000.0

    ret = convert_currency_amount( to_ccy, to_ccy, from_ccy, lock_side, amount, 'spot' )
    print( ret )

    """
    fx_pair = FxPair.get_pair_from_currency( from_ccy, to_ccy )
    price_feed = 'EXTERNAL1'

    x = get_initial_market_state( from_ccy, to_ccy, price_feed=price_feed )
    print( x )
    raise

    spot_rate = get_recent_spot_rate( fx_pair, price_feed )
    print( 'spot', spot_rate )

    outright = get_recent_fwd_outright( fx_pair, price_feed, '1M' )
    print( 'outright', outright )

    fwd_points = get_recent_fwd_points( fx_pair, price_feed, Date.from_int(20240423) )
    print( 'fwd points', fwd_points )
    """

if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    # only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
