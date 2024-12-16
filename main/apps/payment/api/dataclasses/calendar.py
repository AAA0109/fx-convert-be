from datetime import date, datetime
from dataclasses import dataclass
from typing import List, Optional
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class ValueDate(JsonDictMixin):
    date: date
    date_type: str
    fee: float
    fee_unit: str
    tradable: bool
    executable_time: Optional[datetime] = None


@dataclass
class ValueDateCalendar(JsonDictMixin):
    dates: List[ValueDate]
