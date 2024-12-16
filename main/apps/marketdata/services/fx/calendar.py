from typing import Optional, Tuple, List

from hdlib.DateTime.Date import Date

from main.apps.currency.models import FxPair, FxPairTypes
from main.apps.marketdata.models import TradingCalendar
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.util import get_or_none


class CalendarService:
    # The day on which calendars start in the database.
    # calendar_starts = Date.from_int(20210802)
    calendar_starts = Date.from_int(20220816)

    def __init__(self, fx_spot_provider: FxSpotProvider = FxSpotProvider()):
        self._fx_spot_provider = fx_spot_provider

    def can_trade_fx_on_date(self, fx_pair: FxPair, date: Date) -> bool:
        # Fallback for when date is before we started scraping calendars.
        if date < CalendarService.calendar_starts:
            spot = self._fx_spot_provider.get_eod_spot(fx_pair=fx_pair, date=date)
            return spot is not None

        # Check the calendars.Adding 5 days look back and look forward window,
        # OMS will actually handle logic for trade execution on the correct date
        calendar = TradingCalendar.get_calendar_for_pair(fx_pair=fx_pair, start_date_begin=date - 5,
                                                         start_date_end=date + 5)
        if len(calendar) == 0:
            return False

        for session in calendar:
            if session.is_closed:
                continue
            if session.start_date <= date < session.end_date:
                return True

        return False

    def can_trade_or_trade_inverse_on_date(self, fx_pair: FxPairTypes, date: Date) -> bool:
        # Fallback for when date is before we started scraping calendars.
        if date < CalendarService.calendar_starts:
            spot = self._fx_spot_provider.get_eod_spot(fx_pair=fx_pair, date=date)
            return spot is not None

        # Check the calendars.

        pair = FxPair.get_pair(fx_pair)
        fx_pairs = (pair, FxPair.get_pair(pair.inverse_name))
        calendars = TradingCalendar.get_calendars_for_pairs(fx_pairs=fx_pairs,
                                                            start_date_begin=date,
                                                            start_date_end=date)
        for calendar in calendars:
            if not calendar.is_closed:
                return True
        return False

    @get_or_none
    def next_fx_trade_date(self, fx_pair: FxPair, date: Date, include_today: bool = True) -> Optional[TradingCalendar]:
        pair = FxPair.get_pair(fx_pair)
        if not pair:
            return None

        filters = {"pair": pair}
        if include_today:
            filters["date__gte"] = date
        else:
            filters["date__gte"] = date.start_of_next_day()

        return TradingCalendar.objects.filter(**filters).order_by('start_datetime').first()

    def get_traded_pairs_at_time(self, time: Date) -> List[FxPair]:
        traded_pairs = []
        for cal in TradingCalendar.objects.filter(start_datetime__gte=time, end_datetime__lte=time):
            traded_pairs.append(cal.pair)
        return traded_pairs
