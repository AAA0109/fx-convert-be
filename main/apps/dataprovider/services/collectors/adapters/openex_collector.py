import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from croniter import croniter
from django.conf import settings

from main.apps.dataprovider.services.collectors.collector import BaseCollector
from main.apps.dataprovider.services.collectors.publisher import GcpPubSub
from main.apps.dataprovider.services.collectors.quote_tick import QuoteTickFactory, TICK_TYPES, QUOTE_TYPE, QuoteTick
from main.apps.oems.backend.ccy_utils import check_direction
from main.apps.oems.backend.utils import sleep_for
from main.apps.oems.services.brokers.openex import OpenExClient

logger = logging.getLogger(__name__)


# ==========================

class OpenExCollector:
    """
    This is an example rfq collector.
    It can be run independently or attached to a runner.
    """

    source = 'OER'

    def __init__(self, collector_nm, bases=None, app_id=settings.OER_APP_ID, schedule='* * * * *', writer=None,
                 cache=None, publisher=None, max_workers=1, **kwargs):

        if not bases:
            bases = ['USD']
            
        self.api = OpenExClient(app_id)
        self.collector = BaseCollector(collector_nm, self.source, writer=writer, cache=cache, publisher=publisher)
        self.schedule = schedule
        self.iter = croniter(schedule)
        self.next_update = self.iter.get_next()
        self.instruments = bases
        self.factory = QuoteTickFactory(collector=collector_nm, source=self.source,
                                        tick_type=TICK_TYPES.QUOTE, quote_type=QUOTE_TYPE.RFQ,
                                        indicative=True, data_class=QuoteTick)
        self.max_workers = max_workers

    def update_latest(self, base: str):

        latest = self.api.get_latest(base=base, show_bid_ask=False)
        if not latest: return

        dtime = datetime.fromtimestamp(latest['timestamp'])

        for cntr, rate in latest['rates'].items():

            # check for inverted pair and flip bid/ask + rate
            instrument = f'{base}{cntr}-SPOT'

            try:
                invert = check_direction(base, cntr)
                if invert:
                    instrument = f'{cntr}{base}-SPOT'
            except:
                logger.debug(f'failed {cntr}')
                invert = False

            # print( rate, instrument, invert )

            if isinstance(rate, (float, int)):
                if invert:
                    rate = 1 / rate
                bid_rate = ask_rate = mid_rate = float(rate)
            else:
                if invert:
                    bid_rate = 1 / rate['bid']
                    ask_rate = 1 / rate['ask']
                    mid_rate = 1 / rate['mid']
                else:
                    bid_rate = rate['bid']
                    ask_rate = rate['ask']
                    mid_rate = rate['mid']

            self.collector.collect(factory=self.factory,
                                   instrument=instrument,
                                   bid=bid_rate,
                                   bid_time=dtime,
                                   ask=ask_rate,
                                   ask_time=dtime,
                                   mid=mid_rate,
                                   )

    def rfq(self):
        if len(self.instruments) > 1 and self.max_workers > 1:
            # could also use aiohttp
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                responses = list(executor.map(self.update_latest, self.instruments))
        else:
            for base in self.instruments:
                self.update_latest(base)

    def cycle(self, now, flush=True):
        if now > self.next_update:
            logger.info(f'updating {now} {self.next_update}')
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
            self.collector.close()


# ============

if __name__ == "__main__":
    collector = OpenExCollector(f'{settings.APP_ENVIRONMENT}1', ['USD'], publisher=GcpPubSub)
    collector.run_forever()
