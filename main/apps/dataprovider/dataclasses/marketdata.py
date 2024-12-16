from dataclasses import dataclass
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class FxRates(JsonDictMixin):
    rate: float
    rate_ask: float
    rate_bid: float


@dataclass
class FwdPoints(JsonDictMixin):
    fwd_points: float
    fwd_points_ask: float
    fwd_points_bid: float
