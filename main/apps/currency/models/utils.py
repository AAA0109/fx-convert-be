
from main.apps.currency.models import FxPair, Currency

# ===================================================================
# rounding conventions

def bankers_rounding( amount: float, rfact: int ) -> float:
    # this is just python rounding in python. also called half-even.
    return round(amount, rfact)

# ===================================================================
# NOTE: for now to be flexible. Take a dictionary for this information
# replace these in future

def get_currency_ref( ccy_nm ):
    if not hasattr(get_currency_ref, 'cache'):
        get_currency_ref.cache = {
            'INR': { 'exec_amount_rfact': -3 }
        }
    try:
        return get_currency_ref.cache[ccy_nm]
    except KeyError:
        return {}

def get_market_ref( fxpair_nm ):
    if not hasattr(get_market_ref, 'cache'):
        get_market_ref.cache = {}
    try:
        return get_market_ref.cache[fxpair_nm]
    except KeyError:
        return {}

# ===================================================================
# NOTE: these could be a dunder method off Currency and FxPair

DEFAULT_EXEC_AMOUNT_RFACT=0
DEFAULT_EXEC_RATE_RFACT=9
DEFAULT_DISPLAY_QUOTE_RFACT=4
DEFAULT_QUOTE_RFACT=6

def round_execution_amount( ccy: Currency, amount: float ) -> float:
    # currency rounding execution convention here
    ccy_ref = get_currency_ref( ccy.get_mnemonic() )
    exec_amount_rfact = ccy_ref.get('exec_amount_rfact',DEFAULT_EXEC_AMOUNT_RFACT)
    return bankers_rounding( amount, exec_amount_rfact )

def round_execution_rate( fxpair: FxPair, rate: float ) -> float:
    mkt_ref = get_market_ref( fxpair.market )
    exec_rate_rfact = mkt_ref.get('exec_rate_rfact',DEFAULT_EXEC_RATE_RFACT)
    return bankers_rounding( rate, exec_rate_rfact )

def display_round_quote( fxpair:FxPair, rate: float ) -> float:
    mkt_ref = get_market_ref( fxpair.market )
    display_quote_rfact = mkt_ref.get('display_quote_rfact',DEFAULT_DISPLAY_QUOTE_RFACT)
    return bankers_rounding( rate, display_quote_rfact )

def round_quote( fxpair: FxPair, rate: float ) -> float:
    mkt_ref = get_market_ref( fxpair.market )
    quote_rfact = mkt_ref.get('quote_rfact', DEFAULT_QUOTE_RFACT)
    return bankers_rounding( rate, quote_rfact )

# ==============================================

