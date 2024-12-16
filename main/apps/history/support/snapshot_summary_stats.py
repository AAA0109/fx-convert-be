from typing import Optional, Sequence

import numpy as np
import pandas as pd
import logging

from hdlib.DateTime.Date import Date

logger = logging.getLogger(__name__)


class SnapshotSummaryStats(object):
    def __init__(self,
                 company: str = "",
                 summary_name: str = "",
                 start_date: Optional[Date] = None,
                 end_date: Optional[Date] = None,
                 initial_cash_npv: Optional[float] = None,
                 remaining_cash_npv: Optional[float] = None,
                 remaining_hedge_value: Optional[float] = None,
                 initial_hedge_value: Optional[float] = None,
                 final_hedged_value: Optional[float] = None,
                 final_unhedged_value: Optional[float] = None,
                 realized_hedge_pnl: Optional[float] = None,
                 unrealized_hedge_pnl: Optional[float] = None,
                 variance_of_hedged: Optional[float] = None,
                 variance_of_unhedged: Optional[float] = None,
                 total_cashflows_recieved: Optional[float] = None,
                 margin_start: Optional[float] = None,
                 margin_end: Optional[float] = None,
                 roll_costs: Optional[float] = None):
        """
        Construct a summary staticics object for an account.
        :param company: str, company identifier
        :param summary_name: str, customizable name for the summary (e.g. the account name, or test identifier)
        :param start_date: Date, the start of the data set used by the summary (first hedge date)
        :param end_date: Date, the end of the data set used by the summary (last hedge date)
        :param initial_cash_npv: float, initial Net Present Value (NPV) of all future cashflows in the hedge horizon
            as of the start_date, denominated in domestic currency
        :param remaining_cash_npv: float, the remaining NPV as of end_date of cashflows that did not roll-off during
            the test  window, [start_date, end_date]
        :param remaining_hedge_value: float, the remaining NPV as of end_date of the FX positions in the hedge account
        :param final_hedged_value: float, the final hedged account value as of end_date, in domestic currency
        :param final_unhedged_value: float, the final unhedged account value as of end_date, in domestic currency
        :param realized_hedge_pnl: float, the realized PnL resulting from trading activity in the FX hedge account,
            which is one component of the final_hedged_value
        :param unrealized_hedge_pnl: float, the unrealized PnL of the remaining FX positions in the hedge account,
            which is one component of the final_hedged_value
        :param variance_of_hedged: float, a measure of cumulative realized variance of the hedged account value
            over the test period (note, this is unnormalized, and only used as relative measure vs unhedged account)
        :param variance_of_unhedged: float, a measure of cumulative realized variance of the unhedged account value
            over the test period (note, this is unnormalized, and only used as relative measure vs unhedged account)
        :param total_cashflows_recieved: float, the value of all cashflows recieved over  (start_date, end_date],
            converted to domestic current based on spot FX rate at the cashflow pay_date
        :param margin_start: float, an estimate of the Initial Margin requirement for the hedge positions as of
            start_date
        :param margin_end:  float, an estimate of the Initial Margin requirement as of end_date (for the remaining
            hedge positions)
        :param roll_costs: float, an estimate of the roll costs that were (or would have been) incurred over the
            period [start_date, end_date]. These are the financing charges to roll the spot FX hedge positions
            on a nightly basis into the next business date.
        """
        self.company = company
        self.summary_name = summary_name  # Used to identify this snapshot (e.g. an account, a test run)
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash_npv = initial_cash_npv
        self.remaining_cash_npv = remaining_cash_npv
        self.remaining_hedge_value = remaining_hedge_value
        self.initial_hedge_value = initial_hedge_value
        self.final_hedged_value = final_hedged_value
        self.final_unhedged_value = final_unhedged_value
        self.realized_hedge_pnl = realized_hedge_pnl
        self.unrealized_hedge_pnl = unrealized_hedge_pnl
        self.variance_of_hedged = variance_of_hedged
        self.variance_of_unhedged = variance_of_unhedged
        self.total_cashflows_recieved = total_cashflows_recieved
        self.margin_start = margin_start
        self.margin_end = margin_end
        self.roll_costs = roll_costs  # Negative is a rebate

    @property
    def vol_reduction(self) -> float:
        """ The reduction in PnL vol of the hedged relative to unhedged """
        return 1 - np.sqrt(self.variance_of_hedged / self.variance_of_unhedged) \
            if self.variance_of_unhedged > 0 else np.nan

    @property
    def num_dates(self) -> int:
        """ Number of dates in the snapshot window """
        return Date.days_between(start=self.start_date, end=self.end_date) + 1

    def to_dict(self) -> dict:
        out = self.__dict__
        out['num_dates'] = self.num_dates
        out['vol_reduction'] = self.vol_reduction
        return out

    def to_series(self) -> pd.Series:
        as_dict = self.to_dict()
        return pd.Series(data=as_dict.values(), index=as_dict.keys())

    def to_file(self, fpath: str):
        self.to_series().to_csv(fpath)

    def __str__(self):
        return str(self.to_series()) + f"\nvol_reduction:{14 * ' '}{self.vol_reduction}\n"

    @staticmethod
    def merge_stats(snapshots: Sequence['SnapshotSummaryStats']) -> pd.DataFrame:
        if len(snapshots) < 1:
            raise ValueError("You must supply at least one snapshot")

        return pd.concat([snap.to_series() for snap in snapshots], axis=1)
