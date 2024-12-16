import os
import sys

from hdlib.Core.Currency import all_major_currency
from scripts.lib.only_local import only_allow_local


def initialize_IB():
    from main.apps.account.models import Broker

    Broker.create_broker("IBKR")


def initialize_currencies():
    from main.apps.currency.models import Currency

    # Add all the major currencies to the database.
    for name, currency in all_major_currency.items():
        Currency.create_currency_from_hdl(currency)


def initialize_market_convention():
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
             # "USD/CNY": 1000,  # Not supported on IB
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
                continue
        FxMarketConvention.create_or_update_traded_pair(fx_pair=fx_pair, min_lot_size=lot_size)

        # Also Add the inverse pair if it doesnt exist
        FxPair.create_reverse_pair(fx_pair=fx_pair)


# def initialize_margin_rates():
#     from main.apps.hedge.models.margin import FxSpotMargin
#     from main.apps.marketdata.models import DataCut
#     from main.apps.account.models import Broker
#     from main.apps.hedge.models.margin import CurrencyMargin
#
#     # Get the earliest data cut. Use this to set fx spot margin.
#     earliest_cut = DataCut.objects.order_by("cut_time").first()
#     ib = Broker.get_broker("IBKR")
#
#     # Maintenance margins from IB, as of 28-May-2022.
#     margin_rates = {
#         "AED": 0.05,
#         "AUD": 0.03,
#         "CAD": 0.025,
#         "CHF": 0.03,
#         "CNH": 0.06,
#         "CZK": 0.05,
#         "DKK": 0.05,
#         "EUR": 0.03,
#         "GBP": 0.03,
#         "HKD": 0.06,
#         "HUF": 0.05,
#         "ILS": 0.05,
#         "JPY": 0.03,
#         "KRW": 0.10,
#         "MXN": 0.06,
#         "NOK": 0.03,
#         "NXD": 0.03,
#         "PLN": 0.05,
#         "RUB": 0.30,
#         "SAR": 0.05,
#         "SEK": 0.03,
#         "SGD": 0.05,
#         "THB": 0.10,
#         "TRY": 0.30,
#         "USD": 0.025,
#         "ZAR": 0.07
#     }
#     for pair, rate in margin_rates.items():
#         CurrencyMargin.set_rate(currency=pair, rate=rate, broker=ib)


def initialize_interest_rate():
    from main.apps.account.models import Broker
    from main.apps.currency.models import Currency
    from main.apps.hedge.models import InterestRate

    IBKR = Broker.get_broker("IBKR")
    # USD
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("USD"),
                          tier_from=0, tier_to=10000, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("USD"),
                          tier_from=10000, tier_to=None, rate=0.0108)
    # AED
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("AED"),
                          tier_from=0, tier_to=35000, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("AED"),
                          tier_from=35000, tier_to=None, rate=0.00794)
    # AUD
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("AUD"),
                          tier_from=0, tier_to=14000, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("AUD"),
                          tier_from=14000, tier_to=140000, rate=0.00902)
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("AUD"),
                          tier_from=140000, tier_to=None, rate=0.01152)
    # CAD
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("CAD"),
                          tier_from=0, tier_to=13000, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=Currency.get_currency("CAD"),
                          tier_from=13000, tier_to=None, rate=0.00844)
    # CNH
    currency = Currency.get_currency("CNH")
    tier1, rate1 = 65000, 0.005
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=0, tier_to=tier1, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=tier1, tier_to=None, rate=rate1)

    # CZK
    currency = Currency.get_currency("CZK")
    tier1, rate1 = 1000000, 0.06514
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=0, tier_to=tier1, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=tier1, tier_to=None, rate=rate1)

    # DKK
    currency = Currency.get_currency("DKK")
    tier1, rate1 = 300000, -0.00897
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=0, tier_to=tier1, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=tier1, tier_to=None, rate=rate1)

    # EUR
    currency = Currency.get_currency("EUR")
    tier1, rate1 = 50000, -0.00821
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=0, tier_to=tier1, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=tier1, tier_to=None, rate=rate1)

    # GBP
    currency = Currency.get_currency("GBP")
    tier1, rate1 = 8000, -0.00703
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=0, tier_to=tier1, rate=0.0)
    InterestRate.set_rate(broker=IBKR, currency=currency,
                          tier_from=tier1, tier_to=None, rate=rate1)


def run():
    # initialize_currencies()
    # initialize_market_convention()
    # initialize_IB()
    initialize_interest_rate()


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
