from abc import ABC
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, validator
from main.apps.marketdata.models.ref.instrument import InstrumentTypes

allowed_instruments = [item.value for item in InstrumentTypes]


class PriceType(str, Enum):
    upper_bound = 'upper_bound'
    lower_bound = 'lower_bound'

    @staticmethod
    def get_price_type_enum(key: str):
        if key == PriceType.upper_bound.value:
            return PriceType.upper_bound
        elif key == PriceType.lower_bound.value:
            return PriceType.lower_bound


class BaseOrderConfig(BaseModel, ABC):
    pass


class TimeOrderConfig(BaseOrderConfig):
    time_threshold: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @validator('time_threshold', pre=True)
    def time_threshold_validate(cls, v):
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(v)


class PriceOrderConfig(BaseOrderConfig):
    model_config = ConfigDict(use_enum_values=True)

    price_type: PriceType
    price_threshold: Optional[float]


class InstrumentOrderConfig(BaseOrderConfig):
    amount: Union[float, int]
    pair_id: int

    class Meta:
        abstract = True


class MetaOrderConfig(BaseOrderConfig):
    cashflow_id: Optional[int]
    payment_id: Optional[int]


class SpotOrderConfig(InstrumentOrderConfig):
    pass


class ForwardOrderConfig(InstrumentOrderConfig):
    delivery_date: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @validator('delivery_date', pre=True)
    def delivery_date_validate(cls, v):
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(v)


class OrderConfigs(BaseModel):
    configs: List[
        Union[
            TimeOrderConfig,
            PriceOrderConfig,
            MetaOrderConfig,
            ForwardOrderConfig,
            SpotOrderConfig,
            BaseOrderConfig
        ]
    ]
