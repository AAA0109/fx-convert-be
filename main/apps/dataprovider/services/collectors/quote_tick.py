from dataclasses import dataclass, asdict
from datetime import datetime

from main.apps.oems.backend.utils import jsonify


# from collections import defaultdict


# ==================

@dataclass(slots=True)
class QuoteTick:
    collector: str
    source: str
    tick_type: str
    quote_type: str
    time: datetime
    indicative: bool
    instrument: str
    bid: float = None
    ask: float = None
    mid: float = None
    bid_size: float = None
    ask_size: float = None
    bid_time: datetime = None
    ask_time: datetime = None
    bid_expiry: datetime = None
    ask_expiry: datetime = None
    mkt_cond: str = None
    custom: str = None

    def __init__(self, collector, source, tick_type, quote_type, indicative, instrument,
                 bid=None, ask=None, mid=None, bid_size=None, ask_size=None,
                 bid_time=None, ask_time=None, bid_expiry=None, ask_expiry=None,
                 mkt_cond=None, **kwargs):
        self.collector = collector
        self.source = source
        self.tick_type = tick_type
        self.quote_type = quote_type
        self.indicative = indicative
        self.instrument = instrument
        self.time = datetime.utcnow()
        self.bid = bid
        self.ask = ask
        self.mid = mid
        self.bid_size = bid_size
        self.ask_size = ask_size
        self.bid_time = bid_time
        self.ask_time = ask_time
        self.bid_expiry = bid_expiry
        self.ask_expiry = ask_expiry
        self.mkt_cond = mkt_cond
        self.custom = jsonify(kwargs) if kwargs else None

    def export_to_json(self):
        return jsonify(asdict(self))

    def export_to_row(self):
        return self.__slots__

    def export_bq(self):
        data = asdict(self)
        # Convert datetime fields to ISO format
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def get_avro_schema(cls):
        # Define your Avro schema. This could also be loaded from a .avsc file if you prefer.
        return ({
            "type": "record",
            # "doc": "",
            # "namespace": "User.v1",
            # "aliases": ["user-v1", "super user"],
            "name": cls.__name__,
            "fields": [
                {"name": "collector", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "instrument", "type": "string"},
                {"name": "tick_type", "type": "string"},
                {"name": "quote_type", "type": "string"},
                {"name": "time", "type": {
                    "type": "long",
                    "logicalType": "timestamp-micros"
                },
                 },
                {"name": "indicative", "type": "boolean"},
                {"name": "bid", "type": ["double", "null"], "default": None},
                {"name": "ask", "type": ["double", "null"], "default": None},
                {"name": "mid", "type": ["double", "null"], "default": None},
                {"name": "bid_size", "type": ["double", "null"], "default": None},  # should these be ints or longs?
                {"name": "ask_size", "type": ["double", "null"], "default": None},
                {"name": "bid_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "ask_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "bid_expiry", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "ask_expiry", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros",
                }, "null"], "default": None,
                 },
                {"name": "mkt_cond", "type": ["string", "null"], "default": None},
                {"name": "custom", "type": ["string", "null"], "default": None},
            ]
        })


# ==================================

class TICK_TYPES:
    QUOTE = 'quote'
    TRADE = 'trade'
    MKT_STATE = 'mkt_state'
    AUCTION = 'auction'
    IRREG = 'irreg'
    CORP_ACT = 'corp_act'
    REFERENCE = 'reference'


class QUOTE_TYPE:
    RFQ = 'rfq'
    RFS = 'rfs'


# ==================================

class QuoteTickFactory:

    def __init__(self, collector=None, source=None, tick_type=TICK_TYPES.QUOTE, quote_type=QUOTE_TYPE.RFQ,
                 indicative=False, data_class=QuoteTick):
        self.collector = collector
        self.source = source
        self.tick_type = tick_type
        self.quote_type = quote_type
        self.indicative = indicative
        self.data_class = data_class

    # self.oid        = randint(0, 10000000000)

    def get_bucket_key(self, record):
        bucket = '_'.join([record.source, record.instrument, record.tick_type])
        key = record.time.strftime('%Y%m%d')
        return bucket, key

    def __call__(self, instrument=None, **kwargs):
        record = self.data_class(self.collector, self.source, self.tick_type, self.quote_type, self.indicative,
                                 instrument, **kwargs)
        bucket, key = self.get_bucket_key(record)
        return record, bucket, key


# ==================================

@dataclass(slots=True)
class Bucket:
    collector: str
    source: str
    time: datetime
    indicative: bool
    instrument: str
    created_time: datetime
    start_time: datetime
    end_time: datetime

    bid_ticks: int
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    bid_twap: float
    bid_vwap: float
    bid_volume: float
    bid_high_time: datetime
    bid_low_time: datetime

    ask_ticks: int
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    ask_twap: float
    ask_vwap: float
    ask_volume: float
    ask_high_time: datetime
    ask_low_time: datetime

    mid_ticks: int
    mid_open: float
    mid_high: float
    mid_low: float
    mid_close: float
    mid_twap: float
    mid_vwap: float
    mid_volume: float
    mid_high_time: datetime
    mid_low_time: datetime

    spread_ticks: int
    spread_open: float
    spread_high: float
    spread_low: float
    spread_close: float
    spread_twap: float
    spread_vwap: float
    spread_volume: float
    spread_high_time: datetime
    spread_low_time: datetime

    trade_ticks: int
    trade_open: float
    trade_high: float
    trade_low: float
    trade_close: float
    trade_twap: float
    trade_vwap: float
    trade_volume: float
    trade_high_time: datetime
    trade_low_time: datetime

    def __init__(self, collector, source, indicative, instrument, **kwargs):
        self.collector = collector
        self.source = source
        self.indicative = indicative
        self.instrument = instrument
        self.time = datetime.utcnow()

        for k, v in kwargs.items():
            setattr(self, k, v)

    def export_to_json(self):
        return jsonify(asdict(self))

    def export_to_row(self):
        return self.__slots__

    @classmethod
    def get_avro_schema(cls):
        # Define your Avro schema. This could also be loaded from a .avsc file if you prefer.
        return ({
            "type": "record",
            # "doc": "",
            # "namespace": "User.v1",
            # "aliases": ["user-v1", "super user"],
            "name": cls.__name__,
            "fields": [
                {"name": "collector", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "instrument", "type": "string"},
                {"name": "time", "type": {
                    "type": "long",
                    "logicalType": "timestamp-micros"
                },
                 },
                {"name": "indicative", "type": "boolean"},
                {"name": "created_time", "type": {
                    "type": "long",
                    "logicalType": "timestamp-micros"
                },
                 },
                {"name": "start_time", "type": {
                    "type": "long",
                    "logicalType": "timestamp-micros"
                },
                 },
                {"name": "end_time", "type": {
                    "type": "long",
                    "logicalType": "timestamp-micros"
                },
                 },

                {"name": "bid_ticks", "type": ["long", "null"], "default": None},
                {"name": "bid_open", "type": ["double", "null"], "default": None},
                {"name": "bid_high", "type": ["double", "null"], "default": None},
                {"name": "bid_low", "type": ["double", "null"], "default": None},
                {"name": "bid_close", "type": ["double", "null"], "default": None},
                {"name": "bid_twap", "type": ["double", "null"], "default": None},
                {"name": "bid_vwap", "type": ["double", "null"], "default": None},
                {"name": "bid_volume", "type": ["double", "null"], "default": None},
                {"name": "bid_high_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "bid_low_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },

                {"name": "ask_ticks", "type": ["long", "null"], "default": None},
                {"name": "ask_open", "type": ["double", "null"], "default": None},
                {"name": "ask_high", "type": ["double", "null"], "default": None},
                {"name": "ask_low", "type": ["double", "null"], "default": None},
                {"name": "ask_close", "type": ["double", "null"], "default": None},
                {"name": "ask_twap", "type": ["double", "null"], "default": None},
                {"name": "ask_vwap", "type": ["double", "null"], "default": None},
                {"name": "ask_volume", "type": ["double", "null"], "default": None},
                {"name": "ask_high_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "ask_low_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },

                {"name": "mid_ticks", "type": ["long", "null"], "default": None},
                {"name": "mid_open", "type": ["double", "null"], "default": None},
                {"name": "mid_high", "type": ["double", "null"], "default": None},
                {"name": "mid_low", "type": ["double", "null"], "default": None},
                {"name": "mid_close", "type": ["double", "null"], "default": None},
                {"name": "mid_twap", "type": ["double", "null"], "default": None},
                {"name": "mid_vwap", "type": ["double", "null"], "default": None},
                {"name": "mid_volume", "type": ["double", "null"], "default": None},
                {"name": "mid_high_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "mid_low_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },

                {"name": "spread_ticks", "type": ["long", "null"], "default": None},
                {"name": "spread_open", "type": ["double", "null"], "default": None},
                {"name": "spread_high", "type": ["double", "null"], "default": None},
                {"name": "spread_low", "type": ["double", "null"], "default": None},
                {"name": "spread_close", "type": ["double", "null"], "default": None},
                {"name": "spread_twap", "type": ["double", "null"], "default": None},
                {"name": "spread_vwap", "type": ["double", "null"], "default": None},
                {"name": "spread_volume", "type": ["double", "null"], "default": None},
                {"name": "spread_high_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "spread_low_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },

                {"name": "trade_ticks", "type": ["long", "null"], "default": None},
                {"name": "trade_open", "type": ["double", "null"], "default": None},
                {"name": "trade_high", "type": ["double", "null"], "default": None},
                {"name": "trade_low", "type": ["double", "null"], "default": None},
                {"name": "trade_close", "type": ["double", "null"], "default": None},
                {"name": "trade_twap", "type": ["double", "null"], "default": None},
                {"name": "trade_vwap", "type": ["double", "null"], "default": None},
                {"name": "trade_volume", "type": ["double", "null"], "default": None},
                {"name": "trade_high_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
                {"name": "trade_low_time", "type": [{
                    "type": "long",
                    "logicalType": "timestamp-micros"
                }, "null"], "default": None,
                 },
            ]
        })


# =========

class BucketFactory:

    def __init__(self, collector=None, source=None,
                 indicative=False, data_class=Bucket):
        self.collector = collector
        self.source = source
        self.indicative = indicative
        self.data_class = data_class

    def get_bucket_key(self, record):
        bucket = '_'.join([record.source, record.instrument])
        key = record.time.strftime('%Y%m%d')
        return bucket, key

    def __call__(self, instrument=None, **kwargs):
        record = self.data_class(self.collector, self.source, self.indicative,
                                 instrument, **kwargs)
        bucket, key = self.get_bucket_key(record)
        return record, bucket, key
