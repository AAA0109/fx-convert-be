from datetime import datetime, timedelta


class Bucketer:

    def __init__(self, bucket_duration_seconds=1, ignore_zero_volume=True, ignore_zero_price=True):
        self.ignore_zero_volume = ignore_zero_volume
        self.ignore_zero_price = ignore_zero_price
        self.bucket_dur_secs = bucket_duration_seconds
        self.bucket_duration = timedelta(seconds=bucket_duration_seconds)
        self.reset()

    def reset(self):
        self.ticks = 0
        self.first = None
        self.last = None
        self.high = None
        self.low = None
        self.last_volume = 0
        self.twap_numerator = 0
        self.vwap_numerator = 0
        self.total_volume = 0
        self.total_time = 0
        self.start_time = None
        self.end_time = None
        self.high_time = None
        self.low_time = None

    def export(self, cur_time):
        return ({'created_time': cur_time,
                 'start_time': self.start_time,
                 'end_time': self.end_time,
                 'ticks': self.ticks,
                 'open': self.first,
                 'high': self.high,
                 'low': self.low,
                 'close': self.last,
                 'twap': self.twap,
                 'vwap': self.vwap,
                 'volume': self.total_volume,
                 'high_time': self.high_time,
                 'low_time': self.low_time})

    @staticmethod
    def snap_start(bucket_dur_secs, cur_time):
        if bucket_dur_secs == 1:
            return cur_time.replace(microsecond=0)
        else:
            # Convert datetime to total seconds since the epoch
            # Find the most recent N-second boundary
            n = bucket_dur_secs
            timestamp = (cur_time.timestamp() // n) * n
            return datetime.fromtimestamp(timestamp)

    def snap_bucket(self, cur_time):
        # This tick is outside the current bucket, should start a new bucket
        # Typically, you'd want to save the current bucket's data before resetting
        ret = self.export(cur_time)
        self.reset()
        self.start_time = self.snap_start(self.bucket_dur_secs, cur_time)
        self.end_time = self.start_time + self.bucket_duration
        if ret['close'] is not None:
            self.first = ret['close']
            self.last = self.first
            time_elapsed = (cur_time - self.start_time).total_seconds()
            self.twap_numerator += self.first * (time_elapsed - self.total_time)
            self.total_time = time_elapsed
        return ret

    def check_for_bucket(self, cur_time):
        return self.end_time and (cur_time >= self.end_time)

    def add_tick(self, cur_time, price, volume):  # bid, ask, bid_size, ask_size):

        ret = None

        if self.start_time is None:
            self.start_time = self.snap_start(self.bucket_dur_secs, cur_time)
            self.end_time = self.start_time + self.bucket_duration

        if self.check_for_bucket(cur_time):
            ret = self.snap_bucket(cur_time)

        if self.ignore_zero_price and (volume == 0.0 or volume is None):
            return ret

        if self.ignore_zero_volume and (volume == 0.0 or volume is None):
            return ret

        # Update open, high, low, close
        if price is not None or volume is not None:
            self.ticks += 1

        if self.first is None:
            self.first = price

        if self.high is None or price > self.high:
            self.high = price
            self.high_time = cur_time

        if self.low is None or price < self.low:
            self.low = price
            self.low_time = cur_time

        self.last = price
        self.last_volume = volume

        # Update TWAP numerator (time-weighted price sum)
        time_elapsed = (cur_time - self.start_time).total_seconds()
        if time_elapsed > 0.0:
            if price is not None:
                self.twap_numerator += price * (time_elapsed - self.total_time)
            self.total_time = time_elapsed

        # Update VWAP numerator (volume-weighted price sum) and total volume
        if volume > 0.0:
            if price is not None:
                self.vwap_numerator += price * volume
            self.total_volume += volume

        return ret

    @property
    def twap(self):
        return self.twap_numerator / self.total_time if self.total_time else None

    @property
    def vwap(self):
        return self.vwap_numerator / self.total_volume if self.total_volume else None


# =========================

class BidAskMidSpreadBucketer:

    def __init__(self, bucket_duration_seconds=1, return_empty=False):

        self.bid_bucketer = Bucketer(bucket_duration_seconds, ignore_zero_volume=False, )
        self.ask_bucketer = Bucketer(bucket_duration_seconds, ignore_zero_volume=False, )
        self.mid_bucketer = Bucketer(bucket_duration_seconds, ignore_zero_volume=False, )
        self.spread_bucketer = Bucketer(bucket_duration_seconds, ignore_zero_volume=False, )
        self.trade_bucketer = Bucketer(bucket_duration_seconds, ignore_zero_volume=True, )
        self.return_empty = return_empty

    def create_bucket(self, cur_time, instrument, bid_tick, ask_tick, mid_tick, spread_tick, trade_tick):

        bucket = {
            'created_time': cur_time,
            'start_time': bid_tick['start_time'],
            'end_time': bid_tick['end_time'],
            'instrument': instrument,
        }

        for k, v in bid_tick.items():
            if k in bucket: continue
            fld = f'bid_{k}'
            bucket[fld] = v

        for k, v in ask_tick.items():
            if k in bucket: continue
            fld = f'ask_{k}'
            bucket[fld] = v

        for k, v in mid_tick.items():
            if k in bucket: continue
            fld = f'mid_{k}'
            bucket[fld] = v

        for k, v in spread_tick.items():
            if k in bucket: continue
            fld = f'spread_{k}'
            bucket[fld] = v

        for k, v in trade_tick.items():
            if k in bucket: continue
            fld = f'trade_{k}'
            bucket[fld] = v

        if bucket['bid_ticks'] == 0 and bucket['ask_ticks'] == 0 and bucket['trade_ticks'] == 0 and not self.return_empty:
            return

        return bucket

    def add_tick(self, cur_time, instrument=None,
            bid=None, bid_size=None, ask=None, ask_size=None,
            trade=None, trade_size=None, **kwargs):

        bid_tick = self.bid_bucketer.add_tick(cur_time, bid, bid_size)
        ask_tick = self.ask_bucketer.add_tick(cur_time, ask, ask_size)

        try:
            mid = (self.ask_bucketer.last + self.bid_bucketer.last) / 2
            spread = (self.ask_bucketer.last - self.bid_bucketer.last) / 2
        except TypeError:
            mid = None
            spread = None

        try:
            mid_volume = (self.ask_bucketer.last_volume + self.bid_bucketer.last_volume) / 2
        except TypeError:
            mid_volume = None

        mid_tick = self.mid_bucketer.add_tick(cur_time, mid, mid_volume)
        spread_tick = self.spread_bucketer.add_tick(cur_time, spread, mid_volume)
        trade_tick = self.trade_bucketer.add_tick(cur_time, trade, trade_size)

        bucket = None
        if bid_tick and ask_tick:
            if False:
                print( instrument )
                print( 'bid tick', instrument, bid_tick )
                print( 'ask tick', instrument, ask_tick )
                print( 'mid tick', instrument, mid_tick )
                print( 'spread tick', instrument, spread_tick )
                print( 'trade tick', instrument, trade_tick)
            bucket = self.create_bucket(cur_time, instrument, bid_tick, ask_tick, mid_tick, spread_tick, trade_tick)

        return bucket


if __name__ == '__main__':

    import random
    import time

    # Example usage
    bucket = Bucketer(bucket_duration_seconds=60)

    for i in range(181):
        tick = bucket.add_tick(datetime.now(), random.uniform(1.0, 1.3), random.randint(1, 10))
        if tick:
            print('found bucket', tick)
        time.sleep(1.0)
