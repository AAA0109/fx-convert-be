from datetime import datetime, time

import pytz

from main.apps.oems.backend.calendar_utils import get_current_or_next_mkt_session, get_value_date_cutoff
from main.apps.oems.backend.trading_utils import get_trading_session


# ===========

def get_best_execution_status(market_name, ref_date=None, check_spot=False):
    if ref_date is None:
        ref_date = datetime.utcnow()

    ts = get_trading_session()

    ret = {
        'market': market_name,
        'recommend': False,
        'session': ts,
        'check_back': None,
        'execute_before': None,
        'unsupported': False,
    }

    is_open, session = get_current_or_next_mkt_session(market_name, ref_date)

    if is_open:

        # TODO: guard sessions for african currencies

        if ts == 'FridayLate' or ts == 'Pre-Tokyo':

            # nxt_session = get_next_mkt_session( market_name, ref_date )

            if ts == 'FridayLate' and check_spot:
                ret['recommend'] = True
            elif ts == 'Pre-Tokyo':
                tz = pytz.timezone('America/New_York')
                now = datetime.now(tz)
                exec_time = datetime.combine(now.date(), time(20, 0))
                ret['recommend'] = False
                ret['check_back'] = exec_time.astimezone(pytz.utc)
            else:
                ret['recommend'] = False

        else:
            ret['recommend'] = True

        ret['execute_before'] = session['gmtt_close']

    else:
        if not session:
            ret['unsupported'] = True
        else:
            ret['check_back'] = session['gmtt_open']

    if not ret['recommend'] and check_spot and ret['check_back']:
        value_date_cutoff = get_value_date_cutoff(market_name, ref_date=ref_date)
        vd_cutoff_utc = value_date_cutoff.astimezone(pytz.utc)
        if ref_date.astimezone(pytz.utc) < vd_cutoff_utc and ret['check_back'] > vd_cutoff_utc:
            ret['recommend'] = True

    # TODO: add time to this call so that we dont execute on the open

    return ret


def get_smart_execution_status(market_name, ref_date=None):
    ...


# ===========


if __name__ == "__main__":
    import django

    django.setup()

    status = get_best_execution_status('USDJPY', check_spot=True)
    print(status)
