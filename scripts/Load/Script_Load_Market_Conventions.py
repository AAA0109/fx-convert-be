"""
Script that adds which FX pairs are market traded, along with their meta data
These are sourced from:
https://www.interactivebrokers.com/en/index.php?f=2222&exch=ibfxpro&showcategories=FX&p=&cc=&limit=100&page=1
"""

import os
import sys

from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.currency.models import Currency
    from main.apps.currency.models.fxpair import FxPair
    from main.apps.marketdata.models.fx.fx_market_convention import FxMarketConvention

    # Lot size dictionary
    pairs = {"AUD/USD": 1000,
             "EUR/USD": 1000,
             "GBP/USD": 1000,
             "KRW/USD": 1000,
             # "NZD/USD": 1000,
             # "SAR/USD": 1000,
             "USD/CAD": 1000,
             "USD/CHF": 1000,
             "USD/CNH": 1000,
             # "USD/CNY": 1000, # Not supported on IB
             "USD/HKD": 1000,
             "USD/ILS": 1000,
             "USD/JPY": 1000,
             "USD/MXN": 1000,
             # "USD/NOK": 1000,
             "USD/RUB": 1000,
             "USD/SAR": 1000,
             # "USD/SEK": 1000,
             "USD/SGD": 1000,
             "USD/TRY": 1000,
             "USD/ZAR": 1000
             }

    # Add all the major currencies to the database.
    for fx_name, lot_size in pairs.items():
        fx_pair = FxPair.get_pair(pair=fx_name)
        if fx_pair is None:
            base, quote = fx_name.split('/')
            status, fx_pair = FxPair.create_fxpair(base=Currency.get_currency(base),
                                                   quote=Currency.get_currency(quote))
            if status.is_error():
                print(f"Could not create Fx pair {fx_name}: {status}")
                continue
            else:
                print(f"Created Fx pair {fx_name}")
        action, _ = FxMarketConvention.create_or_update_traded_pair(fx_pair=fx_pair, min_lot_size=lot_size)
        print(action)

        # Also Add the inverse pair if it doesnt exist
        action, _ = FxPair.create_reverse_pair(fx_pair=fx_pair)
        print(action)


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
