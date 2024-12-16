import logging
import math

from abc import ABC, abstractmethod
from typing import Optional

from main.apps.account.models.autopilot_data import AutopilotData
from main.apps.hedge.dataclasses.hard_limit import AutopilotHardLimits
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition

logger = logging.getLogger(__name__)


class HardLimitsProvider(ABC):
    padding_limit: float

    def __init__(self, padding_limit: Optional[float] = 0) -> None:
        self.padding_limit = padding_limit

    @abstractmethod
    def calculate_hard_limit(self):
        raise NotImplementedError


class AutopilotHardLimitProvider(HardLimitsProvider):
    draft_fwd_position: DraftFxForwardPosition
    autopilot_data: AutopilotData

    def __init__(self, draft_fwd_position: DraftFxForwardPosition, padding_limit: Optional[float] = 0) -> None:
        super().__init__(padding_limit)
        self.draft_fwd_position = draft_fwd_position
        try:
            self.autopilot_data = AutopilotData.objects.get(account=self.draft_fwd_position.account)
        except Exception as e:
            logger.error(f"{e}")
            self.autopilot_data = None

    def calculate_hard_limit(self) -> Optional[AutopilotHardLimits]:
        if not self.autopilot_data:
            return None

        upper_limit = self.autopilot_data.upper_limit
        lower_limit = self.autopilot_data.lower_limit

        sign = math.copysign(1, self.draft_fwd_position.cashflow.amount)

        start_rate = self.draft_fwd_position.estimated_fx_forward_price

        upper_target = (sign * (upper_limit + self.padding_limit) + 1) * start_rate
        lower_target = (sign * (lower_limit + self.padding_limit) + 1) * start_rate

        return AutopilotHardLimits(
            upper_target=upper_target,
            lower_target=lower_target
        )
