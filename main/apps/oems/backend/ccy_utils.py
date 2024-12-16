import logging
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair

# from main.apps.oems.backend.utils import load_yml, Expand
# CCY_RANKS = load_yml( Expand(__file__) + '/../cfgs/ccy_order.yml' )
# PREMIUM_CCY_RANKS = load_yml( Expand(__file__) + '/../cfgs/ccy_order.yml' )

logger = logging.getLogger(__name__)

CCY_RANKS = [
    'XAG',
    'XAU',
    'BTC',
    'ETH',
    'EUR',
    'GBP',
    'AUD',
    'NZD',
    'USD',
    'CAD',
    'CHF',
    'NOK',
    'SEK',
    'BRL',
    'MXN',
    'HKD',
    'TRY',
    'ZAR',
    'PLN',
    'HUF',
    'CZK',
    'SGD',
    'CNY',
    'CNH',
    'KRW',
    'INR',
    'RUB',
    'TWD',
    'THB',
    'MYR',
    'ILS',
    'IDR',
    'CLP',
    'COP',
    'PEN',
    'PHP',
    'ARS',
    'JPY',
    'NGN',
    'KES',
    'UGX',
]


def check_direction(ccy1, ccy2):
    try:
        from_rank = CCY_RANKS.index(ccy1)
    except:
        from_rank = 10000
    try:
        to_rank = CCY_RANKS.index(ccy2)
    except:
        if ccy1 == 'USD':
            return False
        raise ValueError
    return (to_rank < from_rank)


class TradingSides:
    BUY = 'Buy'
    SELL = 'Sell'
    BUY_SELL = 'Buy/Sell'  # for swaps
    SELL_BUY = 'Sell/Buy'  # for swaps


def determine_rate_side(from_ccy: Currency, to_ccy: Currency):
    logger.debug(f"determine_rate_side input: from_ccy={from_ccy.mnemonic}, to_ccy={to_ccy.mnemonic}")

    if from_ccy is None:
        from_ccy = to_ccy
        fxpair = FxPair.get_pair_from_currency(to_ccy, to_ccy)
        side = 'Buy'

    if to_ccy is None:
        to_ccy = from_ccy
        fxpair = FxPair.get_pair_from_currency(from_ccy, from_ccy)
        side = 'Sell'

    if isinstance(from_ccy, str):
        from_ccy = Currency.get_currency(currency=from_ccy)

    if isinstance(to_ccy, str):
        to_ccy = Currency.get_currency(currency=to_ccy)

    try:
        from_rank = CCY_RANKS.index(from_ccy.get_mnemonic())
    except ValueError:
        from_rank = 100000

    try:
        to_rank = CCY_RANKS.index(to_ccy.get_mnemonic())
    except:
        to_rank = 100000

    if to_rank < from_rank:
        # print( 'buying', to_ccy, from_ccy )
        fxpair = FxPair.get_pair_from_currency(to_ccy, from_ccy)
        side = 'Buy'
    else:
        # print('selling', from_ccy, to_ccy )
        fxpair = FxPair.get_pair_from_currency(from_ccy, to_ccy)
        side = 'Sell'

    logger.debug(f"determine_rate_side output: fxpair={fxpair}, side={side}")
    return fxpair, side

# =========================================
