import json
import logging
import traceback
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Union

import pytz
import redis
from django.conf import settings

from main.apps.account.models import Company
from main.apps.broker.models import CurrencyFee, Broker
from main.apps.broker.services.fee import BrokerFeeProvider
from main.apps.broker.services.forward_points import ForwardPointProvider
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models import CorpayFxSpot
from main.apps.marketdata.services.cutoff_service import CutoffProvider
from main.apps.marketdata.services.fx.fx_provider import CachedFxSpotProvider, FxForwardProvider
from main.apps.marketdata.services.fx.fx_provider import FxForward
from main.apps.oems.backend.calendar_utils import get_current_or_next_mkt_session, get_spot_dt
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.models import CnyExecution
from main.apps.oems.services.currency_execution import CompanyCnyExecutionProvider

# ===========================================
logger = logging.getLogger(__name__)


# TODO: add all standard tenors
class Tenor:
    SPOT = 'spot'
    _1M = '1M'


class Frequency:
    DAILY = 'daily'


# ==========

# development.OER_USDNOK-SPOT_quote
def get_cache_key(env, mkt, price_feed, tenor):
    return f'{env}.{price_feed}_{mkt}-{tenor}_quote'


def get_recent_spot_rate(fx_pair, price_feed='OER', tenor='SPOT'):
    if not hasattr(get_recent_spot_rate, 'conn'):
        if settings.REDIS_URL:
            get_recent_spot_rate.conn = redis.Redis.from_url(
                settings.REDIS_URL)

    if isinstance(fx_pair, str):
        fx_pair = FxPair.get_pair(fx_pair)

    cache_key = get_cache_key(settings.APP_ENVIRONMENT,
                              fx_pair.market, price_feed, tenor)

    date = bid = ask = mid = None

    try:
        # print('checking', cache_key)
        # cached_data = cache.get(cache_key)
        cached_data = get_recent_spot_rate.conn.get(cache_key)
        if cached_data:
            cached_data = json.loads(cached_data)
            date = datetime.fromisoformat(cached_data['time'])
            bid = cached_data['bid']
            ask = cached_data['ask']
            mid = cached_data['mid']
        else:
            logger.debug(f'cache miss: {cache_key}')
    except:
        traceback.print_exc()
        logger.debug(f'cache miss: {cache_key}')

    if date is None or mid is None:
        # get corpay spot
        try:
            logger.debug(f'fetching latest corpay spot price {fx_pair.market}')
            latest_spot = CorpayFxSpot.objects.filter(
                pair=fx_pair).latest('date')
            date = latest_spot.date
            bid = latest_spot.rate_bid
            ask = latest_spot.rate_ask
            mid = latest_spot.rate
        except:
            date = bid = ask = mid = None

    # if not bid:
    #     FxForward.objects.filter(pair=fxpair, data_cut=data_cut)

    return {'date': date, 'bid': bid, 'ask': ask, 'mid': mid}


# ==========

def get_recent_fwd_points(fx_pair, value_date, price_feed='OER'):
    cache_key = get_cache_key(settings.APP_ENVIRONMENT,
                              fx_pair.market, price_feed, value_date.isoformat())

    try:
        # TODO: lookup in feed
        # cached_data = cache.get(cache_key)
        cached_data = None
        # return here
    except:
        pass

    spot_provider = CachedFxSpotProvider()
    fwd_provider = FxForwardProvider(fx_spot_provider=spot_provider)

    # TODO: lookup default tenors by market
    tenors = ['SN', '1W', '2W', '3W', '1M',
              '2M', '3M', '4M', '5M', '6M', '9M', '1Y']
    curve = fwd_provider.get_forward_bid_ask_curve(
        pair=fx_pair.market, tenors=tenors)

    # If I just pass the value date to curve function I got
    # descriptor 'date' for 'datetime.datetime' objects doesn't apply to a 'datetime.date' object
    # So I need to convert value_date to datetime instance
    value_date = datetime(year=value_date.year,
                          month=value_date.month, day=value_date.day)
    fwd_points = curve.points_at_D(value_date)
    spread_points = curve.spread_at_D(value_date)
    fwd_points_bid = fwd_points - (spread_points / 2)
    fwd_points_ask = fwd_points + (spread_points / 2)

    return {'date': value_date.date(), 'bid': fwd_points_bid, 'ask': fwd_points_ask, 'mid': fwd_points}


def get_recent_fwd_outright(fx_pair, tenor, price_feed='OER'):
    cache_key = get_cache_key(settings.APP_ENVIRONMENT,
                              fx_pair.market, price_feed, tenor)

    try:
        # TODO: lookup in feed
        # cached_data = cache.get(cache_key)
        cached_data = None
        # return here
    except:
        pass

    # lookup FxForward here for tenor
    try:
        latest = FxForward.objects.filter(
            pair=fx_pair, tenor=tenor).latest('date')
        date = latest.date
        bid = latest.rate_bid
        ask = latest.rate_ask
        mid = latest.rate
    except:
        date = bid = ask = mid = None

    return {'date': date, 'bid': bid, 'ask': ask, 'mid': mid}


# ============

MAJORS = ('AUD', 'GBP', 'NZD', 'EUR')


def get_ccy_legs(mkt):
    base = mkt[:3]
    cntr = mkt[3:]

    if base in MAJORS:
        base_ccy = f'{base}USD'
        bm = True
    else:
        base_ccy = f'USD{base}'
        bm = False

    if cntr in MAJORS:
        cntr_ccy = f'{cntr}USD'
        cm = True
    else:
        cntr_ccy = f'USD{cntr}'
        cm = False

    return base_ccy, cntr_ccy, bm, cm


def ccy_triangulate_rate(base_ccy, base_rate, cntr_ccy, cntr_rate, base_multiply, cntr_multipy):
    if base_multiply:
        if cntr_multipy:
            rate = base_rate / cntr_rate
        else:
            rate = base_rate * cntr_rate
    else:
        if cntr_multipy:
            breakpoint()
            raise NotImplementedError  # cant happen?
        else:
            rate = cntr_rate / base_rate

    return rate


def ccy_triangulate(base_ccy, base_rate, cntr_ccy, cntr_rate, base_multiply, cntr_multipy):
    date = min(base_rate['date'], cntr_rate['date'])
    bid = None
    ask = None
    mid = None

    # print('here', base_ccy, cntr_ccy, base_multiply, cntr_multipy )
    # print( base_rate['mid'], cntr_rate['mid'] )
    # print( base_rate['mid']*cntr_rate['mid'], base_rate['mid']/cntr_rate['mid'], cntr_rate['mid']/base_rate['mid'] )

    if base_multiply:
        if cntr_multipy:
            mid = base_rate['mid'] / cntr_rate['mid']
            bid = base_rate['ask'] / cntr_rate['ask']
            ask = base_rate['bid'] / cntr_rate['bid']
        else:
            mid = base_rate['mid'] * cntr_rate['mid']
            bid = base_rate['bid'] * cntr_rate['bid']
            ask = base_rate['ask'] * cntr_rate['ask']
    else:
        if cntr_multipy:
            raise NotImplementedError  # cant happen?
            mid = cntr_rate['mid'] * base_rate['mid']
            ask = cntr_rate['bid'] * base_rate['ask']
            bid = cntr_rate['ask'] * base_rate['bid']
        else:
            mid = cntr_rate['mid'] / base_rate['mid']
            bid = cntr_rate['bid'] / base_rate['ask']
            ask = cntr_rate['ask'] / base_rate['bid']

    return {'date': date, 'bid': bid, 'ask': ask, 'mid': mid}


# ===

def get_recent_data(fxpair: FxPair, tenor: Tenor, price_feed: str = 'OER', spot_dt: date = None, last=True):
    if not spot_dt:
        spot_dt, valid_days, spot_days = get_spot_dt(fxpair.market)

    triangulate = ('USD' not in fxpair.market)

    if triangulate:
        base_ccy, cntr_ccy, bm, cm = get_ccy_legs(fxpair.market)
        base_fx_pair = FxPair.get_pair(base_ccy)
        cntr_fx_pair = FxPair.get_pair(cntr_ccy)
        base_spot_rate = get_recent_spot_rate(base_fx_pair, price_feed)
        cntr_spot_rate = get_recent_spot_rate(cntr_fx_pair, price_feed)
        spot_rate = ccy_triangulate(
            base_ccy, base_spot_rate, cntr_ccy, cntr_spot_rate, bm, cm)
    else:
        spot_rate = get_recent_spot_rate(fxpair, price_feed)

    fwd_points = {'date': spot_rate['date'],
                  'bid': 0.0, 'ask': 0.0, 'mid': 0.0}
    outright = None  # TODO: return outright

    if isinstance(tenor, date):
        if tenor > spot_dt:
            # pull spot(s) and add interpolated points to value date
            if last:
                if triangulate:
                    base_fwd_points = get_recent_fwd_points(
                        base_fx_pair, tenor, price_feed=price_feed)
                    cntr_fwd_points = get_recent_fwd_points(
                        cntr_fx_pair, tenor, price_feed=price_feed)
                    base_outright = {'date': base_fwd_points['date'],
                                     'bid': base_spot_rate['bid'] + base_fwd_points['bid'],
                                     'ask': base_spot_rate['ask'] + base_fwd_points['ask'],
                                     'mid': base_spot_rate['mid'] + base_fwd_points['mid']}  # add points to spot
                    cntr_outright = {'date': cntr_fwd_points['date'],
                                     'bid': cntr_spot_rate['bid'] + cntr_fwd_points['bid'],
                                     'ask': cntr_spot_rate['ask'] + cntr_fwd_points['ask'],
                                     'mid': cntr_spot_rate['mid'] + cntr_fwd_points[
                                         'mid']}  # add points to spot # add points to spot
                    outright = ccy_triangulate(base_ccy, base_outright, cntr_ccy, cntr_outright, bm,
                                               cm)  # triangulate outright
                    fwd_points = {'date': outright['date'], 'bid': outright['bid'] - spot_rate['bid'],
                                  'ask': outright['ask'] - spot_rate['ask'], 'mid': outright['mid'] - spot_rate['mid']}
                else:
                    fwd_points = get_recent_fwd_points(
                        fxpair, tenor, price_feed=price_feed)
            else:
                # pull spot(s) and add interpolated forward points for each day to value date
                raise NotImplementedError

    elif tenor != Tenor.SPOT:
        # contant tenor
        if last:
            if triangulate:
                base_outright = get_recent_fwd_outright(
                    base_fx_pair, tenor, price_feed=price_feed)
                cntr_outright = get_recent_fwd_outright(
                    cntr_fx_pair, tenor, price_feed=price_feed)
                outright = ccy_triangulate(base_ccy, base_outright, cntr_ccy, cntr_outright, bm,
                                           cm)  # triangulate outright
            else:
                outright = get_recent_fwd_outright(
                    fxpair, tenor, price_feed=price_feed)
            fwd_points = {'date': outright['date'], 'bid': outright['bid'] - spot_rate['bid'],
                          'ask': outright['ask'] - spot_rate['ask'], 'mid': outright['mid'] - spot_rate['mid']}
        else:
            raise NotImplementedError

    ws_feed = None

    return spot_rate, fwd_points, ws_feed


# ======================

def convert_currency_amount(desired_currency, buy_currency, sell_currency, lock_side, amount, value_date=Tenor.SPOT,
                            rate=None, **kwargs):
    if desired_currency.mnemonic == lock_side.mnemonic:
        return amount

    fxpair, side = determine_rate_side(sell_currency, buy_currency)

    if rate is None:
        spot_rate, fwd_points, ws_feed = get_recent_data(
            fxpair, value_date, **kwargs)
        rate = (spot_rate['bid'] + fwd_points['bid']
                ) if side == 'Sell' else (spot_rate['ask'] + fwd_points['ask'])

    if buy_currency.mnemonic == lock_side.mnemonic:
        if side == 'Sell':
            cntr_amount = amount / rate
        else:
            cntr_amount = amount * rate
    else:
        if side == 'Sell':
            cntr_amount = amount * rate
        else:
            cntr_amount = amount / rate

    return cntr_amount


# =======

def get_fees(company, fxpair, tenor, spot_dt, side):
    is_spot = True
    if isinstance(tenor, date):
        if tenor > spot_dt:
            is_spot = False
    elif tenor != Tenor.SPOT:
        is_spot = False

    ret = {
        "quote_fee": 0,
        "fee": 0,
    }

    if not CnyExecution.objects.filter(company=company, fxpair=fxpair).exists():
        return ret
    cny_execution = CnyExecution.objects.get(company=company, fxpair=fxpair)
    if is_spot:
        broker = Broker.objects.get(broker_provider=cny_execution.spot_broker)
    else:
        broker = Broker.objects.get(broker_provider=cny_execution.fwd_broker)

    try:
        fees = CurrencyFee.get_fees(
            currencies=[
                fxpair.base_currency,
                fxpair.quote_currency
            ],
            broker=broker,
            is_spot=is_spot
        )
        if fees.exists():
            fees = max(fees, key=lambda x: x.pangea_fee)
            multiplier = 1
            if side == "Sell":
                multiplier = -1
            ret['quote_fee'] = (fees.broker_fee + fees.pangea_fee) * multiplier
            ret['fee'] = 0

    except CurrencyFee.DoesNotExist:
        return ret
    # get fee for broker for buy/sell currency
    return ret


def get_initial_market_state(sell_currency: Currency, buy_currency: Currency, tenor: Tenor = Tenor.SPOT,
                             frequency: Frequency = Frequency.DAILY, lock_side=None, amount=None,
                             price_feed='OER', last=True, company: Company = None):
    tz = pytz.timezone('America/New_York')
    tdy = datetime.now(tz).date()
    cutoff_time = tz.localize(datetime.combine(
        tdy, time(16))).astimezone(pytz.timezone('UTC'))

    if sell_currency == buy_currency:
        ccy = buy_currency.get_mnemonic()
        mkt = f'{ccy}{ccy}'
        side = None
        rate_rfact = 1
        spot_dt, valid_days, spot_days = get_spot_dt(mkt)
        status = get_best_execution_status(mkt)

        # Adjust cutoff time
        cutoff_provider = CutoffProvider(market=mkt, session=status['session'])
        cutoff_time = cutoff_provider.modify_cutoff(cutoff_time=cutoff_time)
        status = cutoff_provider.modify_best_exec_status_for_weekend(cutoff_time=cutoff_time,
                                                                     org_best_exec_status=status)
        fxpair = FxPair.get_pair(f"{sell_currency}{buy_currency}")
        broker = get_initial_state_broker(company=company, fxpair=fxpair, tenor=tenor, spot_dt=spot_dt)

        rate = 1.0
        company_fee_svc = BrokerFeeProvider(company=company)
        wire_fee = company_fee_svc.get_wire_fee(fxpair=fxpair, tenor=Tenor.SPOT,
                                                spot_dt=spot_dt, side=side)

        ret = {
            'market': mkt,
            'value_date': spot_dt,
            'rate_rounding': rate_rfact,
            'side': side,
            'spot_date': spot_dt,
            'spot_rate': rate,
            'rate': rate,
            'fwd_points': 0.0,
            'fwd_points_str': "0.0 / 0.0%",
            'implied_yield': 0.0,
            'indicative': False,
            'cutoff_time': cutoff_time,
            'as_of': datetime.utcnow(),
            'channel_group_name': None,
            'status': status,
            'fee': 0,
            'quote_fee': 0,
            'wire_fee': wire_fee,
            'broker_fee': "0.0 / 0.0%",
            'pangea_fee': "0.0 / 0.0%",
            'all_in_reference_rate': 1.0,
            'executing_broker': None if broker is None else broker,
            'is_same_currency': True
        }

        # Adding is_ndf and fwd_rfq_type field
        cny_exec = CompanyCnyExecutionProvider(company=company, fx_pair=mkt)
        is_ndf, fwd_rfq_type = cny_exec.is_ndf()
        ret['is_ndf'] = is_ndf
        ret['fwd_rfq_type'] = fwd_rfq_type

        return ret

    fxpair, side = determine_rate_side(sell_currency, buy_currency)
    market = fxpair.market

    spot_dt, valid_days, spot_days = get_spot_dt(market)
    status = get_best_execution_status(market)

    # Adjust cutoff time
    cutoff_provider = CutoffProvider(market=market, session=status['session'])
    cutoff_time = cutoff_provider.modify_cutoff(cutoff_time=cutoff_time)
    status = cutoff_provider.modify_best_exec_status_for_weekend(cutoff_time=cutoff_time,
                                                                 org_best_exec_status=status)

    # TODO: could support RTP as separate tenor bc pricing will be different

    try:
        spot_rate, fwd_points, ws_feed = get_recent_data(
            fxpair, tenor, price_feed, spot_dt=spot_dt, last=last)
        sr = spot_rate['ask'] if side == 'Buy' else spot_rate['bid']
        fp = fwd_points['ask'] if side == 'Buy' else fwd_points['bid']
    except:
        traceback.print_exc()
        sr = None
        fp = None
        ws_feed = None

    # determine fwd points sign
    fwd_points_svc = ForwardPointProvider()
    fp = fwd_points_svc.determine_fwd_points_sign(fwd_point=fp, side=side)

    if sr is None:
        all_in_rate = None
    else:
        all_in_rate = sr + fp
    iy = 0.0  # TODO: convert fwd points into yield. 0.0 if spot.

    ref = get_reference_data(market)
    if ref:
        rate_rfact = ref.get('QT_SPEC', 4)
    else:
        rate_rfact = 4

    if rate_rfact is not None:
        try:
            sr = round(sr, rate_rfact)
        except:
            pass
        try:
            all_in_rate = round(all_in_rate, rate_rfact)
        except:
            pass

    if isinstance(fp, float) and fp != 0.0 and isinstance(tenor, date):
        days = (tenor - spot_dt).days
        iy = round((fp / sr), 4)

    fees = get_fees(company, fxpair, tenor, spot_dt, side)

    pangea_fee = ""
    broker_fee = ""
    wire_fee = 0
    all_in_reference_rate = None
    if sr is not None:
        sr = round((all_in_rate - fp) / 1 + fees['quote_fee'], 5)
        company_fee_svc = BrokerFeeProvider(company=company)
        bkr_fee, bkr_fee_pct = company_fee_svc.get_indicative_broker_fee(rate=sr, fxpair=fxpair,
                                                                         tenor=tenor, spot_dt=spot_dt, side=side)
        pan_fee, pan_fee_pct = company_fee_svc.get_indicative_pangea_fee(rate=sr, fxpair=fxpair,
                                                                         tenor=tenor, spot_dt=spot_dt, side=side)
        wire_fee = company_fee_svc.get_wire_fee(fxpair=fxpair, tenor=tenor, spot_dt=spot_dt, side=None)
        broker_fee = company_fee_svc.to_fee_expression(
            fee=bkr_fee, fee_pct=bkr_fee_pct)
        pangea_fee = company_fee_svc.to_fee_expression(
            fee=pan_fee, fee_pct=pan_fee_pct)
        all_in_reference_rate = round(bkr_fee + fp + sr, 4)

    # cosmetic fee calculation
    fp_str = fwd_points_svc.to_fwd_point_expression(fwd_point=fp, rate=all_in_rate)
    broker = get_initial_state_broker(company=company, fxpair=fxpair, tenor=tenor, spot_dt=spot_dt)

    ret = {
        'market': market,
        'value_date': tenor,
        'rate_rounding': rate_rfact,
        'side': side,
        'spot_date': spot_dt,
        'spot_rate': sr,
        'rate': all_in_rate,
        'fwd_points': fp,
        'fwd_points_str': fp_str,
        'implied_yield': iy,
        'indicative': True,
        'cutoff_time': cutoff_time,
        'as_of': datetime.utcnow(),
        'channel_group_name': ws_feed,
        'status': status,
        'fee': fees['fee'],
        'quote_fee': fees['quote_fee'],
        'wire_fee': wire_fee,
        'broker_fee': broker_fee,
        'pangea_fee': pangea_fee,
        'all_in_reference_rate': all_in_reference_rate,
        'executing_broker': None if broker is None else broker,
        'is_same_currency': False
    }

    # Adding is_ndf and fwd_rfq_type field
    cny_exec = CompanyCnyExecutionProvider(company=company, fx_pair=market)
    is_ndf, fwd_rfq_type = cny_exec.is_ndf()
    ret['is_ndf'] = is_ndf
    ret['fwd_rfq_type'] = fwd_rfq_type

    return ret

def get_initial_state_broker(company:Company, fxpair:FxPair, tenor:Union[str, date],
                             spot_dt:date) -> Optional[Broker]:
    is_spot = True
    if isinstance(tenor, date):
        if tenor > spot_dt:
            is_spot = False
    elif tenor != 'spot':
        is_spot = False

    try:
        cny_execution = CnyExecution.objects.get(company=company,
                                                 fxpair=fxpair)
    except CnyExecution.DoesNotExist as e:
        try:
            cny_execution = CnyExecution.objects.get(company=company,
                                                     fxpair=FxPair.get_inverse_pair(pair=fxpair))
        except CnyExecution.DoesNotExist as e:
            cny_execution = None

    broker = None
    if cny_execution is not None:
        if is_spot:
            broker = Broker.objects.get(
                broker_provider=cny_execution.spot_broker)
        else:
            broker = Broker.objects.get(
                broker_provider=cny_execution.fwd_broker)
    return broker

# ===============================


class InitialMarketDataProvider:
    sell_currency: Currency
    buy_currency: Currency
    tenor: Union[str, date]
    frequency: str
    price_feed: str
    last: bool
    fx_pair: FxPair
    side: str
    lock_side: Currency
    amount: float
    company: Company

    def __init__(self, sell_currency: Currency, buy_currency: Currency, tenor: Union[str, date],
                 frequency: Frequency = Frequency.DAILY, price_feed: str = 'OER', company=None, lock_side=None,
                 amount=None, last: bool = True) -> None:
        self.sell_currency = sell_currency
        self.buy_currency = buy_currency
        self.tenor = tenor
        if isinstance(self.tenor, str):
            self.tenor = self.tenor.lower()
        self.frequency = frequency
        self.price_feed = price_feed
        self.lock_side = lock_side
        self.amount = amount
        self.cntr_amount = None
        self.last = last
        self.fx_pair, self.side = determine_rate_side(
            sell_currency, buy_currency)
        self.company = company

    def get_initial_market_state(self) -> dict:
        return get_initial_market_state(
            sell_currency=self.sell_currency,
            buy_currency=self.buy_currency,
            tenor=self.tenor,
            frequency=self.frequency,
            price_feed=self.price_feed,
            lock_side=self.lock_side,
            amount=self.amount,
            last=self.last,
            company=self.company
        )

    def get_recent_data(self) -> dict:
        spot_rate, fwd_points, ws_feed = get_recent_data(
            fxpair=self.fx_pair,
            tenor=self.tenor,
            spot_dt=get_spot_dt(mkt=self.fx_pair.market),
            price_feed=self.price_feed,
            last=self.last,
        )
        return {
            'spot_rate': spot_rate,
            'fwd_points': fwd_points,
            'channel_group_name': ws_feed,
        }
