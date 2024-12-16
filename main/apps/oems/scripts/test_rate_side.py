from unittest import skip

from main.apps.currency.models import FxPair
from main.apps.oems.backend.ccy_utils import determine_rate_side, Currency


@skip("Test script exclude from unit test")
def run():
    if True:
        base_currency = Currency.get_currency('USD')
        quote_currency = Currency.get_currency('PEN')
        pair = FxPair.get_pair_from_currency(base_currency, quote_currency)
        print(pair.id, pair.market)
    if False:
        base_currency = Currency.get_currency('USD')
        quote_currency = Currency.get_currency('EUR')

        ret = determine_rate_side(base_currency, quote_currency)
        ret2 = determine_rate_side(quote_currency, base_currency)

    if False:
        base_currency = Currency.get_currency('USD')
        quote_currency = Currency.get_currency('JPY')

        ret = determine_rate_side(base_currency, quote_currency)
        ret2 = determine_rate_side(quote_currency, base_currency)
