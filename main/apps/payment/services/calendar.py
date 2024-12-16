from datetime import date as pydate, time, datetime, timedelta
from typing import List
from pytz import timezone

from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.backend.calendar_utils import get_spot_dt, get_ref_date
from main.apps.oems.services.cutoff_time import CutoffTimeProvider
from main.apps.payment.api.dataclasses.calendar import ValueDate, ValueDateCalendar

class DATE_TYPE:
    EXPEDITED = 'EXPEDITED'
    SPOT = 'SPOT'
    MAX_DATE = 'MAX_DATE'
    FORWARD = 'FORWARD'
    TRADE_DATE = 'TRADE_DATE'

class ValueDateCalendarProvider:
    pair: FxPair
    start_date: datetime
    end_date: datetime
    settlement_days: List[pydate]
    TZ = timezone('America/New_York')
    CUT_TIME_HRS = 16

    def __init__(self, pair: str, start_date: datetime, end_date: datetime, min_date=None,
                 max_date=None, expedited=False, spot_only=False) -> None:
        self.pair = FxPair.get_pair(pair=pair)
        self.start_date = start_date
        self.end_date = end_date
        self.min_date = min_date
        self.max_date = max_date

        # THIS IS A HACK AND WRONG
        if start_date > pydate.today():
            start_date = pydate.today()

        self.ref_date = get_ref_date( self.pair.market )
        self.spot_date, self.settlement_days, self.spot_days = get_spot_dt( self.pair.market, ref_dt=self.ref_date,
                                                                           sdt=start_date, edt=end_date )
        if spot_only: self.max_date = self.spot_date
        if not expedited:
            self.min_date = self.spot_date

    def populate_value_dates(self) -> ValueDateCalendar:
        date_generated: List[pydate] = [self.start_date + timedelta(days=x)
                                        for x in range(0, (self.end_date - self.start_date).days + 1)]

        dates:list[ValueDate] = []
        for date in date_generated:

            if date == self.ref_date:
                date_type = DATE_TYPE.TRADE_DATE
            elif date < self.spot_date:
                date_type = DATE_TYPE.EXPEDITED
            elif date == self.spot_date:
                date_type = DATE_TYPE.SPOT
            elif date == self.max_date:
                date_type = DATE_TYPE.MAX_DATE
            else:
                date_type = DATE_TYPE.FORWARD

            fee, fee_unit = self.__calculate_fee(date=date, market_name=self.pair.market)

            dates.append(
                ValueDate(
                    date=date,
                    date_type=date_type,
                    fee=fee,
                    fee_unit=fee_unit,
                    tradable=self.__is_tradable(date=date),
                    executable_time=self.__get_executable_time(date=date)
                )
            )

        # Check if current time (in NY timezone) > NY cut time (4 PM)
        # Set current SPOT date to expedited and non tradable and,
        # Move SPOT date to first next tradeable FORWARD date
        cutoff_time_svc = CutoffTimeProvider()
        if cutoff_time_svc.is_pass_cutoff():
            for date in dates:
                if date.date_type == DATE_TYPE.SPOT:
                    date.date_type = DATE_TYPE.EXPEDITED
                    date.tradable = False
                    continue

                if date.date_type == DATE_TYPE.FORWARD and date.tradable:
                    date.date_type = DATE_TYPE.SPOT
                    break

        return ValueDateCalendar(dates=dates)

    def __is_tradable(self, date: pydate) -> bool:
        if self.min_date and date < self.min_date:
            return False
        if self.max_date and date > self.max_date:
            return False
        if date in self.settlement_days:
            return True
        return False

    def __calculate_fee(self, date: pydate, market_name = None) -> float:
        # TODO: look this up
        if market_name == 'USDUSD':
            return 20.0, "USD"
        return 0.0, "USD"

    def __get_executable_time(self, date: pydate) -> datetime:
        return self.TZ.localize(datetime.combine(date, time(self.CUT_TIME_HRS))) \
            .astimezone(timezone('UTC'))
