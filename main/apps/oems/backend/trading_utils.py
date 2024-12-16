from datetime import datetime
from cachetools import LRUCache
import pytz

from main.apps.oems.backend.utils import load_yml, Expand
from main.apps.marketdata.models.ref.instrument import Instrument

# =============================

def get_reference_data( mkt: str ) -> dict:

    if not hasattr(get_reference_data,'cache'):
        get_reference_data.cache = LRUCache(256)

    try:
        return get_reference_data.cache[mkt]
    except KeyError:
        try:
            instrument = Instrument.objects.get(name=mkt)
        except:
            return None
        out = instrument.reference
        out['SYMBOLOGY'] = instrument.symbology
        get_reference_data.cache[mkt] = out
        return out

    # legacy
    if not hasattr(get_reference_data, 'ref'):
        # TODO: bad way to do this
        path = Expand(__file__) + '/../cfgs/CCY_REFERENCE.yml'
        get_reference_data.ref = load_yml(path)
    if mkt in get_reference_data.ref:
        return get_reference_data.ref[mkt]
    else:
        return None

# =============================
# rounding conventions

def bankers_rounding( amount: float, rfact: int ) -> float:
    # this is just python rounding in python. also called half-even.
    return round(amount, rfact)

def ccy_round_amount( ccy: str, amount: float ) -> float:
    # currency rounding execution convention here
    if ccy == 'INR':
        return bankers_rounding( amount, -3 )
    return bankers_rounding( amount, 2 )

# =============================

def get_trading_session( granular=True, now=None, tz='America/New_York' ):

    now = now or datetime.now(pytz.timezone(tz)) # do this calc in NY time

    if granular:
        dow = now.weekday()
        hr  = now.hour
        mn  = now.minute

        if (dow == 4 and hr >= 17) or (dow == 5) or (dow == 6 and hr < 18):
            return 'Weekend'
        elif dow == 6 and hr < 20:
            # Sunday Early 6:00PM - 8:00PM
            return 'SundayEarly'
        elif dow == 4 and (hr > 15 or (hr == 15 and mn >= 30)):
            # Friday after 3:30PM
            return 'FridayLate'
        elif hr >= 0 and hr < 8:
            # Everyday Midnight -> 8AM
            return 'London'
        elif hr >= 8 and (hr <= 16 or (hr == 16 and mn < 45)):
            # Everyday 8:00AM -> 4:45PM
            return 'NewYork'
        elif hr >= 20:
            return 'Tokyo'
        else:
            # 4:45PM -> 8PM
            return 'Pre-Tokyo'

    dow = now.weekday()
    hr  = now.hour

    if (dow == 4 and hr >= 17) or (dow == 5) or (dow == 6 and hr < 18):
        return 'Weekend'
    elif hr >= 19:
        return 'Tokyo'
    elif hr >= 0 and hr < 8:
        return 'London'
    elif hr >= 8 and hr < 19:
        return 'New York'
    else:
        raise ValueError

if __name__ == "__main__":
    ref = get_reference_data( 'EURUSD' )

