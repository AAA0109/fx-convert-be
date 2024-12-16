"""

LAST is always followed by LAST_SIZE

BID is always followed by BID_SIZE and then by either ASK_SIZE alone or ASK and ASK_SIZE

ASK is always followed by ASK_SIZE

Any SIZE may appear alone

Possible that ASK is always followed by both ASK_SIZE and tghen BID_SIZE but uncertain

Have to figure out how to handle the delayed data since a timestamp is not forthcoming

modify to just send out the changed fields and put all logic in the listener
"""

import atexit
import logging
import queue
import time
import pytz

from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

from ibapi import comm
from ibapi.client import EClient
from ibapi.common import MAX_MSG_LEN, TickerId, TickAttrib
from ibapi.contract import Contract
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.utils import BadMessage
from ibapi.wrapper import EWrapper

from django.conf import settings

from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.backend.utils import sleep_for
from main.apps.oems.backend.api import pangea_client

def _none_cb():
    return None


def _none_dict():
    return defaultdict(_none_cb)

logger = logging.getLogger(__name__)

_non_price_strings = ("SIZE", "OPTION", "VOLUME", "EFP", "YIELD", "EXCH")

from main.apps.dataprovider.services.collectors.quote_tick import QuoteTickFactory, TICK_TYPES, QUOTE_TYPE, BucketFactory
from main.apps.dataprovider.services.collectors.collector import BaseCollector
from main.apps.dataprovider.services.collectors.cache import RedisCache
from main.apps.dataprovider.services.collectors.writer import BucketManager
from main.apps.dataprovider.services.collectors.publisher import BasePublisher, GcpPubSub
from main.apps.dataprovider.services.collectors.bucketer import BidAskMidSpreadBucketer, Bucketer

# =============================================================================

class IbkrTickApi(EClient, EWrapper):

    REQ_ID = 0
    TICK_ID = 0
    DISCONNECTED = 'DISCONNECTED'
    CONNECTED = 'CONNECTED'

    def __init__(self, host, port, clientId: int, collector_nm,
                 mkts=None, futures=None, antispam=True, writer=None, cache=None, publisher=None,
                 disconnect=True, silent=True, limit=0, bucket_secs=60, collect_ticks=False,
                 shutdown_time=None, shutdown_duration=None):

        EClient.__init__(self, self)

        self.source = 'IBKR'

        self.collector = BaseCollector(collector_nm, self.source, writer=writer, cache=cache, publisher=publisher)
        self.quote_factory = QuoteTickFactory(collector=collector_nm, source=self.source,
                                        tick_type=TICK_TYPES.QUOTE, quote_type=QUOTE_TYPE.RFS,
                                        indicative=False)
        self.bucket_factory = BucketFactory(collector=collector_nm, source=f'{self.source}_1MIN', indicative=False)

        self.host = host
        self.port = port
        self.mkts = mkts
        self.futures = futures
        self.antispam = antispam
        self.clientId = clientId
        self._disconnect = disconnect
        self.silent = silent
        self.limit = limit
        self.collect_ticks = collect_ticks
        self.shutdown_time = shutdown_time
        self.shutdown_duration = shutdown_duration
        self.count = 0
        self.bucket_secs = bucket_secs
        self.subscriptions = {}
        self.blank_exchanges = set()
        self.working_exchanges = set()
        self.ib_mult = {}
        self.market_data = {}
        self.status = self.DISCONNECTED
        self.connected = True
        self.do_exit = False
        self._next_bucket = None
        atexit.register(self.close)

    @classmethod
    def get_req_id(cls):
        cls.REQ_ID += 1
        return cls.REQ_ID

    @classmethod
    def get_tick_id(cls):
        cls.TICK_ID += 1
        return cls.TICK_ID

    def change_state( self, state ):
        if state != self.status:
            self.status = state
            logger.info(f'changing state to {self.status} @ {datetime.utcnow().isoformat()}')

    def do_connect(self):

        try:
            logger.info(f'connecting to {self.host} {self.port} {self.clientId}')
            self.connect(self.host, self.port, self.clientId)
            self.connected = (self.conn is not None)
            logger.info(f'connection status {self.connected} {self.conn}')
        except:
            self.connected = False
            try:
                self.conn.disconnect()
                self.conn.socket = None
            except:
                logger.debug('ERROR: could not disconnect properly')
            logger.info(f'connection failed {self.connected} {self.conn}')
            self.conn = None
            if self.do_exit:
                self.change_state(self.DISCONNECTED)
                exit(0)

        self.change_state(self.CONNECTED if self.connected else self.DISCONNECTED)

        return self.connected

    def init(self):

        if not self.mkts and not self.futures:
            raise ValueError

        if self.conn is None:
            if self.do_connect():
                sleep_for(2)
                self.poll(1)
                ret = True
            else:
                ret = False
        else:
            ret = True

        if ret:
            for mkt in self.mkts:
                self.req_mkt_data(mkt)

            for base_fut in self.futures:
                self.req_fut_data( base_fut )

        return ret

    def error(self, reqId, errorCode: int, errorString: str, advancedOrderRejectJson=''):

        handled = False
        if errorCode in (200, 162):  # 162 is market data perms
            logging.debug(f'ERROR: {errorString}')
            handled = True
        elif errorCode == 1100:
            logging.error('lost connectivity')
            handled = True
            if self.connected:
                self.change_state(self.DISCONNECTED)
                self.connected = False
                self.conn = None
        elif errorCode == 1101:
            logging.warn('connectivity restored -- recovering mkt data subscriptions')
            if not self.connected:
                self.connected = True
                self.change_state(self.CONNECTED)
            self.recover_mkt_data()
            handled = True
        elif errorCode == 1102:
            logging.warn('connectivity restored -- mkt data subscriptions not lost')
            if not self.connected:
                self.connected = True
                self.change_state(self.CONNECTED)
            handled = True
        elif errorCode == 1300:
            logging.error('socket dropped -- reconnect and recover mkt data subscriptions')
            # TODO: do we need to stop/start the self.reader?
            self.disconnect()
            self.connected = False
            self.conn = None
            self.change_state(self.DISCONNECTED)
            sleep_for(2.0)
            if self.do_connect():
                self.recover_mkt_data()
            else:
                exit(0)  # ??
            handled = True
        elif errorCode == 101 and 'Max' in errorString:
            if reqId in self.subscriptions:
                logger.error(f"ERROR: ran out of subscriptions... not subscribed to {self.subscriptions[reqId]['master_ticker']}")

        if not handled:
            if not self.silent:
                EWrapper.error(self, reqId, errorCode, 'Data Api -- ' + errorString)

    def poll(self, timeout=0.1, limit=100):

        count = 0
        if not self.reader.is_alive() or not self.isConnected():
            return False
        try:
            while not self.msg_queue.empty():
                try:
                    text = self.msg_queue.get(block=False)
                    if len(text) > MAX_MSG_LEN:
                        self.wrapper.error(NO_VALID_ID, BAD_LENGTH.code(),
                                           "%s:%d:%s" % (BAD_LENGTH.msg(), len(text), text))
                        self.disconnect()
                        break
                except (KeyboardInterrupt, SystemExit):
                    logging.info("detected KeyboardInterrupt, SystemExit")
                    self.keyboardInterrupt()
                    self.keyboardInterruptHard()
                    return None
                except queue.Empty:
                    # this shouldn't happen
                    raise
                else:
                    fields = comm.read_fields(text)
                    logging.debug("fields %s", fields)
                    self.decoder.interpret(fields)
                    count += 1
                    if limit and count >= limit:
                        break
            if not count:
                try:
                    text = self.msg_queue.get(block=True, timeout=timeout)
                    if len(text) > MAX_MSG_LEN:
                        self.wrapper.error(NO_VALID_ID, BAD_LENGTH.code(),
                                           "%s:%d:%s" % (BAD_LENGTH.msg(), len(text), text))
                        self.disconnect()
                        return False
                except (KeyboardInterrupt, SystemExit):
                    logging.info("detected KeyboardInterrupt, SystemExit")
                    self.keyboardInterrupt()
                    self.keyboardInterruptHard()
                    return None
                except queue.Empty:
                    logging.debug("queue.get: empty")
                else:
                    fields = comm.read_fields(text)
                    logging.debug("fields %s", fields)
                    self.decoder.interpret(fields)
                    count += 1
        except (KeyboardInterrupt, SystemExit):
            logging.info("detected KeyboardInterrupt, SystemExit")
            self.keyboardInterrupt()
            self.keyboardInterruptHard()
            return None
        except BadMessage:
            logging.info("BadMessage")
            self.conn.disconnect()
        except Exception as e:
            logging.info('exception %s', e)
            logging.warning('exception %s', e)
            raise
        return True

    def close(self):

        for tickid, sub in self.subscriptions.items():
            self.cancelMktData(tickid)

        try:
            self.reader._stop()
        except:
            pass

        try:

            self.disconnect()
            self.connected = False
            self.conn = None
            self.change_state(self.DISCONNECTED)
        except:
            pass

        logger.info('end run')
        missed = sorted([(info['master_ticker'], info['sym']) for info in self.subscriptions.values() if
                         not info['received_data']])
        if missed:
            logger.info(f'didnt receive data for: {missed}')
        missed2 = sorted([info['master_ticker'] for info in self.subscriptions.values() if not info['received_data']])
        if missed2:
            logger.info(f'didnt receive data for masters {missed2}')
        if self.blank_exchanges:
            logger.info(f'exchanges left out: {sorted(self.blank_exchanges)}')
        if self.working_exchanges:
            logger.info(f'exchanges received: {sorted(self.working_exchanges)}')

        self.subscriptions.clear()
        self.blank_exchanges.clear()
        self.working_exchanges.clear()

    def cycle(self, timeout=1):
        result = self.poll(timeout)
        return result

    @staticmethod
    def wake_time( now_ny ):

        # Calculate days to next Sunday (6 is Sunday in python's weekday, where Monday is 0)
        days_to_next_sunday = (6 - now_ny.weekday()) % 7
        if days_to_next_sunday == 0 and now_ny.hour >= 18:
            # If it's already past 6 PM on Sunday, move to next Sunday
            days_to_next_sunday = 7

        # Calculate the next Sunday at 6 PM
        next_sunday_6pm = now_ny.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=days_to_next_sunday)

        return next_sunday_6pm

    def is_blackout_period( self ):

        # Current NY time
        now_ny = datetime.now(pytz.timezone('America/New_York'))

        # Check if today is Friday after 5PM, or anytime on Saturday, or Sunday before 6PM
        in_blackout = now_ny.weekday() == 4 and now_ny.hour >= 17 or \
                             now_ny.weekday() == 5 or \
                             now_ny.weekday() == 6 and now_ny.hour < 18

        if in_blackout:
            wakeup_date = self.wake_time( now_ny )
            self.close()
            logger.info(f'in blackout period... sleeping until {wakeup_date.isoformat()}')
            target_seconds = (wakeup_date - now_ny).total_seconds()
            logger.info(f'sleeping for {target_seconds}')
            sleep_for( target_seconds )
            return True

        return False

    def next_bucket( self, cur_time ):
        start_time = Bucketer.snap_start(self.bucket_secs, cur_time)
        self._next_bucket = start_time + timedelta(seconds=self.bucket_secs)

    def check_bucket( self, cur_time ):
        if self._next_bucket and cur_time >= self._next_bucket:
            # print('check for bucket', cur_time, self._next_bucket)
            for info in self.subscriptions.values():
                if info['bucketer']:
                    bucket = info['bucketer'].add_tick(cur_time, instrument=info['master_ticker'])
                    if bucket:
                        bucket = self.process_bucket( bucket )
            self.next_bucket(cur_time)

    def check_alive( self ):
        if self.conn:
            if not self.reader.is_alive() or not self.isConnected():
                logger.info(f"Not Connected: {datetime.utcnow().isoformat()}")
                self.close()
                time.sleep(15.0)
                self.init()
        return False

    def run(self):

        if not self.init():
            return False

        if self.bucket_secs and not self._next_bucket:
            self.next_bucket( datetime.utcnow() )

        try:
            while True:
                if self.is_blackout_period():
                    if not self.init():
                        return False
                self.check_alive()
                self.check_bucket( datetime.utcnow() )
                result = self.cycle()
                if result is None:
                    break
                elif not result:
                    if not self.connected and not self.init():
                        sleep_for(10.0)
        except (KeyboardInterrupt, SystemExit):
            logging.info("detected KeyboardInterrupt, SystemExit")
            self.keyboardInterrupt()
            self.keyboardInterruptHard()
        finally:
            self.close()

    # =================

    @staticmethod
    def safe_float( x ):
        try:
            return float(x)
        except:
            return None

    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float,
                              bidSize: Decimal, askSize: Decimal, tickAttribBidAsk):

        super().tickByTickBidAsk(reqId, time, bidPrice, askPrice, bidSize,
                                      askSize, tickAttribBidAsk)

        # print("BidAsk. ReqId:", reqId, "Time:", datetime.fromtimestamp(time).strftime("%Y%m%d-%H:%M:%S"), "BidPrice:", bidPrice, "AskPrice:", askPrice, "BidSize:", bidSize, "AskSize:", askSize, "BidPastLow:", tickAttribBidAsk.bidPastLow, "AskPastHigh:", tickAttribBidAsk.askPastHigh)

        info = self.subscriptions[reqId]

        if not info['received_data']:
            logger.info( f"received tick for {info['master_ticker']}")

        info['received_data'] = True
        self.blank_exchanges.discard(info['contract'].exchange)
        self.working_exchanges.add(info['contract'].exchange)

        if self.antispam and info['last'] == (bidPrice,askPrice):
            return

        info['last'] = (bidPrice,askPrice)
        sym = info['sym']
        instrument = info['master_ticker']

        dt = datetime.fromtimestamp(time)
        bid = self.safe_float(bidPrice)
        ask = self.safe_float(askPrice)
        bid_size = self.safe_float(bidSize)
        ask_size = self.safe_float(askSize)

        try:
            mid = (bid+ask)/2
        except:
            mid = None

        # print( instrument, dt, bid, ask, bid_size, ask_size )

        if self.collector:
            self.collector.collect(
                factory=self.quote_factory,
                instrument=instrument,
                bid=bid,
                bid_size=bid_size,
                bid_time=dt,
                ask=ask,
                ask_size=ask_size,
                ask_time=dt,
                mid=mid,
            )

    def request_tick_data( self, tickid, contract ):
        logger.info(f'subscribing to... {contract}')
        self.reqMktData(tickid, contract, '', False, False, '')
        # self.reqTickByTickData(tickid, contract, "BidAsk", 0, True)

    def recover_mkt_data(self):
        for tickid, info in self.subscriptions.items():
            self.request_tick_data( tickid, info['contract'] )

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float,
                  attrib: TickAttrib):
        info = self.subscriptions[reqId]
        contract = info['contract']
        info['received_data'] = True
        logger.info('Price <' + contract.localSymbol + ', ' + TickTypeEnum.to_str(tickType)
                     + ', ' + str(price) + ', ' + str(attrib) + '>')
        self.tick(info, TickTypeEnum.to_str(tickType), price)

    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        info = self.subscriptions[reqId]
        contract = info['contract']
        info['received_data'] = True
        self.blank_exchanges.discard(contract.exchange)
        self.working_exchanges.add(contract.exchange)
        logger.info('Size <' + contract.localSymbol + ', ' + TickTypeEnum.to_str(tickType)
                     + ', ' + str(size) + '>')
        # self.update_mkt_data(contract, TickTypeEnum.to_str(tickType), None, size)
        self.tick(info, TickTypeEnum.to_str(tickType), size)

    def process_bucket( self, bucket ):
        # print( bucket['instrument'], bucket['end_time'].isoformat() )
        if self.collector and self.bucket_factory:
            self.collector.collect(
                factory=self.bucket_factory,
                **bucket,
            )

    def tick(self, info, field, value):

        ticker = info['master_ticker']

        if ticker not in self.market_data:
            logger.info(f'unexpected onMktData {ticket} {field} {value}')
            return

        non_price = any(x in field for x in _non_price_strings)
        if non_price:
            pass
        else:
            if value <= 0.0:
                # print('API WARN: ignoring negative value', ticker, field, value)
                return
            try:
                value *= self.ib_mult[ticker]
            except:
                logger.info(f'{ticker} {field} {value} :: ib_mult {self.ib_mult}')
                raise

        row = self.market_data[ticker]
        row[field] = value

        if field == 'BID':
            row['BID_TIME'] = datetime.utcnow()
        elif field == 'ASK':
            row['ASK_TIME'] = datetime.utcnow()
        elif field == 'LAST':
            row['LAST_TIME'] = datetime.utcnow()
        elif 'CLOSE' in field:
            logger.info( f'received settlement: {ticker} {field} {value}')
            row['SETTLE_TIME'] = datetime.utcnow()

        if field in ('BID_SIZE','ASK_SIZE','LAST_SIZE') and ('BID' in row or 'ASK' in row or 'LAST' in row):


            bid = row.get('BID',None)
            ask = row.get('ASK',None)
            last = row.get('LAST',None)

            key = (bid,ask,last)

            if self.antispam and info['last'] == key:
                return

            info['last'] = key

            # ======

            bid_size = row.get('BID_SIZE',None)
            ask_size = row.get('ASK_SIZE',None)
            bid_time = row.get('BID_TIME',None)
            ask_time = row.get('ASK_TIME',None)
            last = row.get('LAST',None)
            last_size = row.get('LAST_SIZE',None)
            # settlement = None
            # settle_time = row.get('SETTLE_TIME',None)

            try:
                mid = (bid+ask)/2
            except:
                mid = None

            # print( ticker, row )

            if info['bucketer']:
                bucket = info['bucketer'].add_tick( datetime.utcnow(), instrument=ticker, bid=bid, bid_size=bid_size, ask=ask, ask_size=ask_size, trade=last, trade_size=last_size)
                if bucket:
                    self.process_bucket( bucket )

            if self.collector and self.collect_ticks:
                self.collector.collect(
                    factory=self.quote_factory,
                    instrument=ticker,
                    bid=bid,
                    bid_size=bid_size,
                    bid_time=bid_time,
                    ask=ask,
                    ask_size=ask_size,
                    ask_time=ask_time,
                    mid=mid,
                )

    # ==================================

    def get_ib_contract( self, ref ):

        ib = ref['SYMBOLOGY']['IBKR']

        if ref['INSTR_TYPE'] in ('SPOT', 'NDF', 'FX'):
            contract = Contract()
            contract.symbol = ib['IB_SYMBOL']
            contract.secType = ib['IB_TYPE']
            contract.multiplier = ib['IB_MULT'] or ''
            contract.exchange = ib['IB_EXCHS']
            contract.currency = ib['IB_CCY']
            contract.conId = ib['IB_CONID']
            contract.localSymbol = ib['IB_LOCSYM']
            contract.name = ib['IB_NAME']
            return contract
        else:
            print('unknown instrument', ref['MARKET'], ref['INSTR_TYPE'])
            return

    def req_fut_data(self, base_future, return_data=False):

        contracts = pangea_client.get_active_contracts_by_base( base_future)

        if not contracts:
            logger.info(f'no contracts found {base_future} skipping')
            return False

        for contract in contracts:

            master_ticker = contract['fut_symbol']
            symbol = contract['local_symbol']

            ibc = Contract()
            ibc.symbol = contract['symbol']
            ibc.secType = contract['sec_type']
            ibc.multiplier = contract['multiplier']
            ibc.exchange = contract['exchanges']
            ibc.currency = contract['currency']
            ibc.conId = contract['con_id']
            ibc.localSymbol = contract['local_symbol']
            ibc.name = contract['market_name']

            self.ib_mult[master_ticker] = 1.0
            self.ib_mult[symbol] = 1.0

            tickid = self.get_tick_id()
            self.subscriptions[tickid] = {'sym': symbol, 'contract': ibc, 'master_ticker': master_ticker,
                                          'received_data': False, 'last': None, 'type': 'FUT',
                                          'bucketer': BidAskMidSpreadBucketer(self.bucket_secs) if self.bucket_secs else None}

            self.blank_exchanges.add(ibc.exchange)
            self.market_data[master_ticker] = {}

            self.request_tick_data( tickid, ibc )

        return True

    def req_mkt_data(self, symbol, return_data=False):

        logger.info(f'requesting {symbol}')

        ref = get_reference_data(symbol)
        if not ref:
            logger.info(f'no reference data {symbol} skipping')
            return

        try:
            ticker = ref['SYMBOLOGY']['IBKR']['IB_SYMBOL']
            if not ticker: raise
        except:
            logger.info(f'skipping...{symbol}')
            return

        if ref['INSTR_TYPE'] == 'FX':
            master_ticker = f'{symbol}-{ref["TENOR"]}'
        else:
            master_ticker = symbol

        our_cfact = None
        contract = self.get_ib_contract( ref )
        if not contract: return

        if our_cfact:
            ib_cfact = ref['SYMBOLOGY']['IBKR']['IB_MULT']
            ib_pricemag = ref['SYMBOLOGY']['IBKR']['IB_PRICEMAG']
            ib_cfact = float(ib_cfact) / float(ib_pricemag)
            self.ib_mult[master_ticker] = ib_cfact / our_cfact
            self.ib_mult[symbol] = ib_cfact / our_cfact
        else:
            self.ib_mult[master_ticker] = 1.0
            self.ib_mult[symbol] = 1.0

        if return_data:
            return {'master_ticker': master_ticker,
                    'ticker': ticker,
                    'type': ref['INSTR_TYPE'],
                    'ib_mult': self.ib_mult[ticker],
                    'contract': contract,
                    'last': None, 'bucketer': BidAskMidSpreadBucketer(self.bucket_secs) if self.bucket_secs else None}

        tickid = self.get_tick_id()
        self.subscriptions[tickid] = {'sym': ticker, 'contract': contract, 'master_ticker': master_ticker,
                                      'received_data': False, 'last': None, 'type': ref['INSTR_TYPE'],
                                      'bucketer': BidAskMidSpreadBucketer(self.bucket_secs) if self.bucket_secs else None}

        self.blank_exchanges.add(contract.exchange)
        self.market_data[master_ticker] = {}

        self.request_tick_data( tickid, contract )

        return True

# ============================================================

if __name__ == '__main__':

    host = '127.0.0.1'
    port = 7497

    # USD, AED, AUD, CAD, CHF, CNH, CZK, DKK, EUR, GBP, HKD, HUF, ILS, JPY, MXN, NOK, NZD, PLN, SAR, SEK, SGD, TRY, ZAR
    mkts = ['EURUSD','AUDUSD','GBPUSD','NZDUSD','USDCHF','USDCNH','USDCZK','USDHKD','USDHUF','USDILS','USDJPY','USDMXN','USDNOK','USDPLN','USDSGD','USDTRY','USDZAR']
    futures = ['XID',]

    collector = IbkrTickApi( host, port, 12, f'{settings.APP_ENVIRONMENT}1', mkts=mkts, futures=futures)
    collector.run()

    # Current NY time
    if False:
        now_ny = datetime.now(pytz.timezone('America/New_York'))
        in_blackout = collector.is_blackout_period()
        wake = collector.wake_time( now_ny )
        target_seconds = (wake - now_ny).total_seconds()
        print( now_ny.isoformat(), in_blackout, wake.isoformat(), target_seconds )

