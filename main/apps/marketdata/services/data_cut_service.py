from typing import Optional, Tuple, Sequence, Iterable

import pytz
from django.db import IntegrityError
from hdlib.DateTime.Date import Date

from main.apps.marketdata.models.marketdata import DataCut
from main.apps.util import get_or_none, ActionStatus


class DataCutService:
    """
    A service for handling data cuts and virtual data cuts.
    """

    EOD_TIME = (22, 0, 0, 0)  # Hour, Minute, Second, Microsecond
    BENCHMARK_TIME = (16, 0, 0, 0)

    # ================================================
    # Accessors
    # ================================================

    @staticmethod
    @get_or_none
    def get_eod_cut(date: Optional[Date] = None,
                    cuts: Optional[Sequence[DataCut]] = None) -> Optional[DataCut]:
        """ Get the EOD cut for this date, or None if there is none. """
        if not cuts:
            cuts = DataCutService.get_all_eod_cuts(date=date)
        # If we found an EOD cut on the requested day, return it, else return None.
        if cuts:
            for cut in cuts:
                if date is None or cut.date.date() == date.date():
                    return cut
        return None

    @staticmethod
    def get_all_eod_cuts(date: Optional[Date] = None) -> Iterable[DataCut]:
        filters = {"cut_type": DataCut.CutType.EOD}
        if date is not None:
            # Start one day in the future because for mysterious reasons, sometimes it doesn't work to start on date.
            filters["cut_time__lte"] = date + 1
        return DataCut.objects.filter(**filters).order_by("-cut_time")

    @staticmethod
    def get_eod_cuts_in_range(start_date: Optional[Date] = None, end_date: Optional[Date] = None) -> Iterable[DataCut]:
        filters = {"cut_type": DataCut.CutType.EOD}
        if start_date is not None:
            filters["cut_time__gte"] = start_date
        if end_date is not None:
            filters["cut_time__lte"] = end_date
        return DataCut.objects.filter(**filters).order_by("cut_time")

    @staticmethod
    @get_or_none
    def get_last_eod_cut(date: Date, include_today: bool = False) -> Optional[DataCut]:
        """ Get the last EOD cut on or before this date, or strictly before this date, depending on the flag. """
        filters = {"cut_type": DataCut.CutType.EOD, "cut_time__lte" if include_today else "cut_time__lt": date}
        qs = DataCut.objects.filter(**filters).order_by("-cut_time")
        for cut in qs:
            cut_time = Date.from_datetime(cut.cut_time)
            if cut_time.to_int() == date.to_int():
                continue
            return cut

    @staticmethod
    @get_or_none
    def get_nearest_cut(date: Date,
                        cut_type: DataCut.CutType = DataCut.CutType.EOD,
                        roll_down: bool = True) -> Optional[DataCut]:
        """ Get the EOD cut for the same date. """
        filters = {"cut_type": cut_type}
        if roll_down:
            filters["cut_time__lte"] = date
            return DataCut.objects.filter(**filters).order_by("-cut_time").first()

        filters["cut_time__gte"] = date
        return DataCut.objects.filter(**filters).order_by("cut_time").first()

    @staticmethod
    @get_or_none
    def get_latest_cut(time: Optional[Date] = None):
        if not time:
            return DataCut.objects.order_by("-cut_time").first()
        return DataCut.objects.filter(cut_time__lte=time).order_by("-cut_time").first()

    # ================================================
    # Creators
    # ================================================

    @staticmethod
    def create_cut(date: Date, cut_type: DataCut.CutType) -> Tuple[ActionStatus, Optional['DataCut']]:
        """
        Create a DataCut.
        """
        try:
            cut_time_utc = date.astimezone(pytz.utc)
            time_values = (cut_time_utc.hour, cut_time_utc.minute, cut_time_utc.second, cut_time_utc.microsecond)

            if time_values == DataCutService.EOD_TIME:
                cut_type = DataCut.CutType.EOD
                cut, created = DataCutService._create_or_update_specific_cut(date, cut_type)
            elif time_values == DataCutService.BENCHMARK_TIME:
                cut_type = DataCut.CutType.BENCHMARK
                cut, created = DataCutService._create_or_update_specific_cut(date, cut_type)
            else:
                cut, created = DataCut.objects.get_or_create(
                    cut_time=date,
                    cut_type=cut_type)

            if not created:
                return ActionStatus.no_change(f"Cut already exists at this time: {date}"), cut

            return ActionStatus.log_and_success(f"Create new cut: {date}"), cut
        except IntegrityError as ex:
            cut, created = DataCut.objects.get_or_create(
                cut_time=date)
            return ActionStatus.log_and_success(f"Found existing cut: {date}"), cut
        except Exception as ex:
            return ActionStatus.error(f"{ex}"), None

    # ===========================PRIVATE METHODS===========================
    @staticmethod
    def _create_or_update_specific_cut(date, cut_type):
        cut, created = DataCut.objects.update_or_create(
            cut_time=date,
            defaults={'cut_type': cut_type}
        )
        return cut, created
