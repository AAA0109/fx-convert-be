from dataclasses import dataclass
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class AutopilotHardLimits(JsonDictMixin):
    upper_target: float
    lower_target: float
