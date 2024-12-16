import time
import traceback
import logging

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from croniter import croniter
from django.conf import settings

from main.apps.dataprovider.services.collectors.collector import BaseCollector
from main.apps.dataprovider.services.collectors.quote_tick import QuoteTickFactory, TICK_TYPES, QUOTE_TYPE, QuoteTick
from main.apps.oems.backend.utils import sleep_for
from main.apps.oems.services.brokers.verto import VertoApi

logger = logging.getLogger(__name__)

# ==========================

class VertoRfqCollector:
    """
    This is an example rfq collector.
    It can be run independently or attached to a runner.
    """

    source = 'VERTO'

    def __init__(self, collector_nm, mkts, schedule='* * * * * */30', writer=None, cache=None, publisher=None,
                 max_workers=1):
        self.api = VertoApi()
        self.collector = BaseCollector(collector_nm, self.source, writer=writer, cache=cache, publisher=publisher)
        self.schedule = schedule
        self.iter = croniter(schedule)
        self.next_update = self.iter.get_next()
        self.instruments = mkts
        self.factory = QuoteTickFactory(collector=collector_nm, source=self.source,
                                        tick_type=TICK_TYPES.QUOTE, quote_type=QUOTE_TYPE.RFQ,
                                        indicative=False, data_class=QuoteTick)
        self.max_workers = max_workers

    def bid_quote(self, ccy1: str, ccy2: str):

        # quote tick
        bid_time = datetime.utcnow()
        bid_response = self.get_fx_rate(ccy1, ccy2)

        # how to handle the instrument needs to be thought out
        instrument = f'{ccy1}{ccy2}-SPOT'

        self.collector.collect(factory=self.factory,
                               instrument=instrument,
                               bid=bid_response['rate'],
                               bid_time=bid_time,
                               bid_expiry=bid_response['expiry'],
                               )

    def ask_quote(self, ccy1: str, ccy2: str):

        ask_time = datetime.utcnow()
        ask_response = self.get_fx_rate(ccy2, ccy1)

        # how to handle the instrument needs to be thought out
        ikey = f'{ccy1}{ccy2}-SPOT'

        self.collector.collect(factory=self.factory,
                               instrument=ikey,
                               ask=ask_response['rate'],
                               ask_time=ask_time,
                               ask_expiry=ask_response['ask_expsiry']
                               )

    def two_way_quote(self, instrument: str):

        # ccy1 = USD
        # ccy2 = JPY

        ccy1, ccy2 = instrument[:3], instrument[3:]

        bid_time = datetime.utcnow()
        # from ccy1 to ccy2
        bid_response = self.api.get_fx_rate(ccy1, ccy2)

        ask_time = datetime.utcnow()
        # from ccy2 to ccy1
        ask_response = self.api.get_fx_rate(ccy2, ccy1)

        try:
            bid_rate = bid_response['rate']
        except TypeError:
            bid_rate = None

        try:
            ask_rate = 1.0 / ask_response['rate']
        except TypeError:
            ask_rate = None

        if bid_rate is None and ask_rate is None:
            return

        try:
            mid_rate = (ask_rate + bid_rate) / 2.0
        except:
            mid_rate = None

        # TODO: handled by 3.12
        bid_expiry = datetime.fromisoformat(bid_response['expiry'][:-1]) if bid_response else None
        ask_expiry = datetime.fromisoformat(ask_response['expiry'][:-1]) if ask_response else None

        # how to handle the instrument needs to be thought out
        instrument = f'{ccy1}{ccy2}-SPOT'

        logger.info(f'{bid_time} {instrument} {bid_rate} {ask_rate}')

        self.collector.collect(factory=self.factory,
                               instrument=instrument,
                               bid=bid_rate,
                               bid_time=bid_time,
                               bid_expiry=bid_expiry,
                               ask=ask_rate,
                               ask_time=ask_time,
                               ask_expiry=ask_expiry,
                               mid=mid_rate,
                               )

    def rfq(self):

        if len(self.instruments) > 1 and self.max_workers > 1:
            # could also use aiohttp
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                responses = list(executor.map(self.two_way_quote, self.instruments))
        else:
            for instrument in self.instruments:
                self.two_way_quote(instrument)

    def cycle(self, now, flush=True):
        if now > self.next_update:
            logger.info(f'updating: {now} {self.next_update}')
            try:
                self.rfq()
            except:
                traceback.print_exc()
            if flush: self.collector.flush()
            self.next_update = self.iter.get_next()

    def close(self):
        if self.collector:
            self.collector.close()

    def run_forever(self):
        try:
            while True:
                now = time.time()
                self.cycle(now)
                sleep_for(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()


# ============

if __name__ == "__main__":
    collector = VertoRfqCollector(f'{settings.APP_ENVIRONMENT}1', ['USDJPY', 'EURUSD', 'USDCAD'])
    collector.run_forever()
