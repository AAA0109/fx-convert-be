import pytz

from datetime import datetime
from datetime import date as pydate
from typing import List, Union
from recurrence import Recurrence
from recurrence.fields import RecurrenceField
from dateutil.rrule import rrulestr

from main.apps.currency.models.currency import Currency
from main.apps.oems.services.calendar import CalendarService


class RecurrenceProvider:
    occurrence:Recurrence
    periodicity_start_date:datetime
    periodicity_end_date:datetime

    def __init__(self, periodicity:Union[str, Recurrence], periodicity_start_date:pydate, periodicity_end_date:pydate) -> None:
        self.occurrence = periodicity
        if isinstance(periodicity, str):
            self.occurrence = RecurrenceField().from_db_value(periodicity)
        self.periodicity_start_date = self.periodicity_date_to_datetime(date=periodicity_start_date)
        self.periodicity_end_date = self.periodicity_date_to_datetime(date=periodicity_end_date)

    def get_occurrence_dates(self, sell_currency:Currency, buy_currency:Currency) -> List[datetime]:
        # occurrences = self.occurrence.occurrences()
        rec_dates = [item.date() for item in list(rrulestr(str(self.occurrence)))]
        dates = CalendarService().infer_value_dates(sell_currency=sell_currency, buy_currency=buy_currency,
                                                    dates=rec_dates)
        return dates

    def periodicity_date_to_datetime(self, date: pydate) -> datetime:
        return datetime(
            date.year,
            date.month,
            date.day,
            0, 0, 0, tzinfo=pytz.utc
        )
