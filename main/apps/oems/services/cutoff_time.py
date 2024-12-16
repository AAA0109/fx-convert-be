from datetime import datetime, time
from typing import Optional
from pytz import timezone


class CutoffTimeProvider:
    TZ = timezone('America/New_York')
    CUT_TIME_HRS = 16

    def __init__(self) -> None:
        pass

    def is_pass_cutoff(self, ref_date:Optional[datetime] = None):
        if ref_date is None:
            ref_date = datetime.now(tz=self.TZ)
        # Check if current time (in NY timezone) > NY cut time (4 PM)
        return ref_date.time() > time(hour=self.CUT_TIME_HRS, minute=0, second=0, microsecond=0)
