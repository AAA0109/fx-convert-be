import os, sys

# from scripts.lib.only_local import only_allow_local

"""
Example Script for marking to market a cashflow using forwards
"""


def run():

    from main.apps.marketdata.services.fx.fx_provider import CachedFxSpotProvider, FxForwardProvider
    from hdlib.DateTime.Date import Date

    spot_provider = CachedFxSpotProvider()
    fwd_provider = FxForwardProvider(fx_spot_provider=spot_provider)

    fx_pair = 'EUR/USD'
    value_date = Date.from_int(20240514)

    tenors = ['SN','1W','2W','3W','1M','2M','3M','4M','5M','6M','9M','1Y']
    curve = fwd_provider.get_forward_bid_ask_curve(pair=fx_pair, tenors=tenors)
    fwd_points = curve.points_at_D(value_date)
    spread_points = curve.spread_at_D(value_date)
    fwd_points_bid = fwd_points - (spread_points/2)
    fwd_points_ask = fwd_points + (spread_points/2)
    print( 'mid', fwd_points, 'bid', fwd_points_bid, 'ask', fwd_points_ask )

if __name__ == '__main__':

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()