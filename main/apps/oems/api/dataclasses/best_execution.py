from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Optional
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


class LiquidityValue(Enum):
    LIMITED = 'limited'
    GOOD = 'good'


@dataclass
class BestExecOptionLabel(JsonDictMixin):
    label: str
    value: str


@dataclass
class BestExecStatus(JsonDictMixin):
    market: Optional[str] = None
    recommend: Optional[bool] = None
    session: Optional[str] = None
    check_back: Optional[datetime] = None
    execute_before: Optional[datetime] = None
    unsupported: Optional[bool] = None
    label: Optional[str] = None
    value: Optional[str] = None


@dataclass
class FxSpotInfo(JsonDictMixin):
    spot_value_date: date
    settlement_days: int
    days: int


@dataclass
class LiquidityInsight(JsonDictMixin):
    liquidity: LiquidityValue
