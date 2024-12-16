import logging

logger = logging.getLogger(__name__)


class RollingAum(object):
    def __init__(self,
                 todays_aum: float,
                 rolling_aum: float,
                 actual_days_in_window: int,
                 window_size: int):
        """
        Structure containing the data for rolling Aum (Assets Under Management) calculations
        :param todays_aum: float, the AUM for today
        :param rolling_aum: float, the rolling AUM (including today)
        :param actual_days_in_window: int, the desired number of days in the rolling window (including today)
            for calculating AUM
        :param window_size: int, the actual number of days in the rolling window (including today), when
            calculating AUM. This number can differ from desired days, b/c customer may not have been around
            for the full window
        """
        self.todays_aum = todays_aum
        self.rolling_aum = rolling_aum
        self.actual_days_in_window = actual_days_in_window
        self.window_size = window_size

    @property
    def rolling_aum_sum(self) -> float:
        """
        The sum of AUMs in the window (rather than the rolling average)
        """
        return self.rolling_aum * self.actual_days_in_window
