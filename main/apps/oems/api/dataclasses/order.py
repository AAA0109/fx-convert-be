from dataclasses import dataclass
from typing import List


@dataclass
class BrokerSupportedPairs:
    broker_id: int
    instrument: str
    pair_ids: List[int]


@dataclass
class SupportedPairs:
    supported_pairs: List[BrokerSupportedPairs]


@dataclass
class PairPrice:
    pair_id: int
    price: float


@dataclass
class BrokerInstrumentPrices:
    broker_id: int
    instrument: str
    prices: List[PairPrice]


@dataclass
class PriceCache:
    data: List[BrokerInstrumentPrices]
