from main.apps.marketdata.models import Fx, FxPairTypes, FxPair

from hdlib.DateTime.Date import Date

from django.db import models

from typing import Optional, Sequence, Iterable


class TradingCalendar(Fx):
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    is_closed = models.BooleanField(default=False)

    @staticmethod
    def get_calendar_for_pair(fx_pair: FxPairTypes,
                              start_date_begin: Optional[Date] = None,
                              start_date_end: Optional[Date] = None) -> Optional[Sequence['TradingCalendar']]:
        pair = FxPair.get_pair(fx_pair)
        if not pair:
            return None

        filters = {"pair": pair}
        if start_date_begin:
            filters["start_date__gte"] = start_date_begin.date()
        if start_date_end:
            filters["start_date__lte"] = start_date_end.date()

        return TradingCalendar.objects.filter(**filters).order_by('start_date')

    @staticmethod
    def get_calendars_for_pairs(fx_pairs: Iterable[FxPair],
                                start_date_begin: Optional[Date] = None,
                                start_date_end: Optional[Date] = None) -> Optional[Sequence['TradingCalendar']]:
        filters = {"pair__in": fx_pairs}
        if start_date_begin:
            filters["start_date__gte"] = start_date_begin
        if start_date_end:
            filters["start_date__lte"] = start_date_end

        return TradingCalendar.objects.filter(**filters).order_by('pair', 'start_date')
