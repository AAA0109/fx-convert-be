import logging
import math
from collections import defaultdict

from hdlib.Core.Currency import Currency
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache, DictSpotFxCache
from main.apps.currency.models.fxpair import FxPair, FxPairId, FxPairName, FxPairTypes
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.models.fx.rate import FxForward, FxSpot, FxTypes, FxSpotRange
from main.apps.marketdata.models.fx.estimator import FxSpotCovariance, FxEstimator, FxEstimatorTypes, FxSpotVol
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.util import get_or_none
from main.apps.oems.backend.calendar_utils import SettlementCalendar, parse_tenor
from main.apps.oems.backend.datetime_index import DatetimeIndex

from hdlib.TermStructures.ForwardCurve import ForwardCurve, InterpolatedForwardCurve, FlatForwardCurve
from hdlib.TermStructures.DiscountCurve import DiscountCurve, InterpolatedDiscountCurve
from hdlib.DateTime.DayCounter import DayCounter_HD, DayCounter
from hdlib.DateTime.Date import Date

import numpy as np
import pandas as pd
from typing import List, Union, Sequence, Optional, Dict, Tuple, Iterable

logger = logging.getLogger(__name__)


# =================================
# TODO: this should be a dense time-series object for market data caches
# that means that all the django stuff has to go.

def sorted_list_init():
    return DatetimeIndex(key=lambda x: x.date)


class FIT_TYPES:
    POINTS = 'points'
    SPOT_POINTS = 'spot_points'
    OUTRIGHT = 'outright'


class INTERP_TYPES:
    # non-linear interpolation only after 1Y tenor
    LINEAR = 'linear'
    EXPONENTIAL = 'exponential'
    CUBIC = 'cubic'


# =================================

class FxSpotProvider(object):

    def __init__(self):
        """
        Data provider which provides FxSpot data (points, caches, time series, etc)
        """
        pass

    # =====================================================================================
    #  Spot caches.
    # =====================================================================================

    def _update_cache(self, all_data):
        pass

    def get_spot_cache(self,
                       time: Optional[Date] = None,
                       fxpairs: Optional[Iterable[FxPair]] = None,
                       window: int = 30) -> SpotFxCache:
        """
        Get a cache of spot fx with the most recent spots at or before the requested time. Spots will not be pulled
        from further back in the past than some time window. Either all spots can be specified, or just those from some
        list.
        :param time: Date, the time at which to get the desired cache (it will pull a cache for the latest spots
            no later than the supplied time. If this time does not have spots, it will look backward, as far back
            as some specified window, and pull the nearest spot)
        :param fxpairs: iterable of FxPair (optional), if supplied only get these pairs, else get all pairs
        :param window: int, a time window in days for which we will look backwards for the nearest spot, closest to
            the supplied times
        :return: SpotFxCache, cache of spots found
        """
        if not time:
            date = Date.to_date(Date.now())
        else:
            date = Date.to_date(time)

        if window < 0:
            raise ValueError(f"data window cannot be negative")

        # all_pairs = [entry.pair for entry in FxSpot.objects.distinct("pair")]
        # fx_spots, data_cuts = {}, {}
        # for pair in all_pairs:
        #     entry = FxSpot.objects.filter(data_cut__cut_time__lte=date, pair=pair)\
        #         .order_by("-data_cut__cut_time")\
        #         .first()
        #     fx_spots[pair] = entry.rate
        #     data_cuts[pair] = entry.data_cut.cut_time
        # return DictSpotFxCache(date, fx_spots, data_cuts)

        first_date = (date - window).start_of_day()
        filters = {"data_cut__cut_time__gte": first_date,
                   "data_cut__cut_time__lte": date,
                   "rate__isnull": False}
        if fxpairs:
            filters["pair__in"] = fxpairs
        all_data = FxSpot.objects.filter(**filters).prefetch_related().select_related()

        self._update_cache(all_data)

        fx_spots, cut_time = {}, {}
        for spot in all_data:
            fxpair = spot.pair
            if fxpair in fx_spots:
                # If this is more recent data, add it instead.
                if cut_time[fxpair] < spot.data_time:
                    fx_spots[fxpair] = spot.rate
                    cut_time[fxpair] = spot.data_time
            else:
                fx_spots[fxpair] = spot.rate
                cut_time[fxpair] = spot.data_time
        return DictSpotFxCache(date, fx_spots, cut_time)

    def get_eod_spot_fx_cache(self, date: Optional[Date] = None) -> SpotFxCache:
        """
        Get all fx spots available at EOD on a particular date.

        :param date: Date, the time at which spots are observed
        :return: SpotFxCache, a cache of all the spots
        """
        data_cut = DataCutService.get_eod_cut(date=date)
        return self.get_spot_cache(time=Date.from_datetime(data_cut.cut_time))

    # =====================================================================================
    #  Spot Values
    # =====================================================================================

    def get_spot_value(self, fx_pair: FxTypes, date: Date) -> float:
        try:
            return FxSpot.objects.select_related('data_cut').filter(pair=FxPair.get_pair(fx_pair),
                                         rate__isnull=False,
                                         data_cut__cut_time__lte=date) \
                .order_by("-data_cut__cut_time").first().rate
        except Exception:
            return np.nan

    def get_eod_spot(self, fx_pair: FxTypes, date: Date) -> Optional[float]:
        objs = FxSpot.objects.filter(pair=FxPair.get_pair(fx_pair),
                                     data_cut__cut_time__gt=date.start_of_day(),
                                     data_cut__cut_time__lte=date.start_of_next_day(),
                                     data_cut__cut_type=DataCut.CutType.EOD,
                                     rate__isnull=False)
        return objs[0] if objs else None

    def get_spots(self,
                  data_cut: DataCut = None,
                  pairs: Iterable[Union[FxPair, FxPairId]] = None,
                  min_date: Optional[Date] = None) -> Sequence['FxSpot']:
        filters = {}
        if min_date:
            filters["date__gte"] = min_date

        if not pairs:
            filters['data_cut'] = data_cut
            return FxSpot.objects.filter(**filters)
        if not data_cut:
            filters['pair__in'] = pairs
            return FxSpot.objects.filter(**filters)

        if pairs:
            filters['pair__in'] = pairs
        if data_cut:
            filters['data_cut'] = data_cut

        if len(filters) == 0:
            raise ValueError(f"not enough arguments are non-None to use the get_spots function")

        return FxSpot.objects.filter(**filters)

    def get_spot_rates(self,
                       pair: FxPairTypes,
                       start_date: Optional[Date] = None,
                       end_date: Optional[Date] = None,
                       allow_null: bool = False,
                       ohlc: bool = False) -> Sequence['FxSpot']:
        filters = {"pair": FxPair.get_pair(pair)}
        if start_date:
            filters["data_cut__cut_time__gte"] = start_date
        if end_date:
            filters["data_cut__cut_time__lte"] = end_date
        if not allow_null:
            if ohlc:
                filters["close__isnull"] = False
            else:
                filters["rate__isnull"] = False
        if ohlc:
            return FxSpotRange.objects.filter(**filters).order_by("data_cut__cut_time")
        else:
            return FxSpot.objects.filter(**filters).order_by("data_cut__cut_time")

    def convert_currency_rate(self, from_currency: Currency, to_currency: Currency, amount: float) -> Optional[float]:
        fxpair = FxPair.get_pair_from_currency(from_currency, to_currency)
        result = amount * self.get_spot_value(fxpair, Date.now())
        if math.isnan(result):
            return None
        return result

    # =====================================================================================
    #  Spot Time Series
    # =====================================================================================

    def get_eod_spot_time_series(self,
                                 start_date: Date,
                                 end_date: Date,
                                 fx_pair: FxPairTypes,
                                 ohlc: bool=False) -> Optional[List[Tuple[Date, float]]]:
        output = {} if ohlc else []
        rates = self.get_spot_rates(start_date=start_date, end_date=end_date, pair=fx_pair, ohlc=ohlc)
        for rate in rates:
            if ohlc:
                dt = Date.from_datetime(rate.data_time)
                output[dt] = (dt, rate.open, rate.high, rate.low, rate.close)
            else:
                output.append((Date.from_datetime(rate.data_time), rate.rate))
        return output

    def get_rate_time_series(self,
                             fx_pair: FxTypes,
                             only_eod: bool = True,
                             min_date: Date = None,
                             max_date: Date = None) -> List[Tuple[Date, float]]:
        filters = {"pair": FxPair.get_pair(fx_pair), "rate__isnull": False}
        if only_eod:
            filters["data_cut__cut_type"] = DataCut.CutType.EOD
        if min_date:
            filters['data_cut__cut_time__gte'] = min_date
        if max_date:
            filters['data_cut__cut_time__lte'] = max_date
        data = FxSpot.objects.filter(**filters).order_by("data_cut__cut_time")
        output = []
        for point in data:
            output.append((Date.from_datetime(point.date), point.rate))
        return output

    # =====================================================================================
    #  Date Lookups based on available data
    # =====================================================================================

    @get_or_none
    def get_max_date_for_pair(self, fx_pair: FxTypes, allow_empty_rate: bool = False) -> Date:
        filters = {"pair": FxPair.get_pair(fx_pair)}
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        max_date = FxSpot.objects.filter(**filters).latest('data_cut__cut_time').date
        return Date.from_datetime(max_date)

    @get_or_none
    def get_min_date_for_pair(self, fx_pair: FxTypes, allow_empty_rate: bool = False) -> Date:
        filters = {"pair": FxPair.get_pair(fx_pair)}
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        min_date = FxSpot.objects.filter(**filters).earliest('data_cut__cut_time').date
        return Date.from_datetime(min_date)

    @get_or_none
    def get_min_date(self, allow_empty_rate: bool = False) -> Date:
        filters = {}
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        min_date = FxSpot.objects.filters(**filters).earliest('data_cut__cut_time').date
        return Date.from_datetime(min_date)

    def get_max_date(self, allow_empty_rate: bool = False) -> Date:
        filters = {}
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        max_date = FxSpot.objects.filter(**filters).latest('data_cut__cut_time').date
        return Date.from_datetime(max_date)

    def get_min_common_date(self, fx_pairs: Iterable[FxTypes]) -> Date:
        return np.min([self.get_min_date_for_pair(fx_pair) for fx_pair in fx_pairs])

    def get_max_common_date(self, fx_pairs: Iterable[FxTypes]) -> Date:
        return np.max([self.get_max_date_for_pair(fx_pair) for fx_pair in fx_pairs])

    def get_common_date_range(self, fx_pairs: Iterable[FxTypes]) -> Tuple[Date, Date]:
        return self.get_min_common_date(fx_pairs), self.get_max_common_date(fx_pairs)

    def get_all_dates_for_pair(self, fx_pair: FxTypes, allow_empty_rate: bool = False) -> List[Date]:
        filters = {"pair": FxPair.get_pair(fx_pair)}
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        all_dates = FxSpot.objects.filter(**filters).values('data_cut__cut_time') \
            .distinct().order_by('data_cut__cut_time')
        return [Date.from_datetime_date(date['data_cut__cut_time']) for date in all_dates]

    @get_or_none
    def get_dates_in_range(self,
                           start_date: Date,
                           end_date: Date,
                           fx_pair: FxPair,
                           allow_empty_rate: bool = False) -> Iterable[Date]:
        filters = {
            "date__range": [start_date, end_date],
            "data_cut__cut_type": DataCut.CutType.EOD,
            "pair": fx_pair
        }
        if not allow_empty_rate:
            filters["rate__isnull"] = False
        dates = FxSpot.objects.filter(**filters) \
            .values('data_cut__cut_time') \
            .distinct().order_by('data_cut__cut_time')
        for date in dates:
            yield Date.from_datetime(date["data_cut__cut_time"])


# ============

class CachedFxSpotProvider(FxSpotProvider):
    def __init__(self):
        super().__init__()
        self.cache = defaultdict(sorted_list_init)

    def get_fx(self, ref_date=None, fx_pair=None, cut_id=1):
        try:
            data = self.cache[(fx_pair, cut_id)]
            i = data.find(ref_date, comp='le')
            if i is None:
                cut_id = DataCut.CutType.INTRA.value
                data = self.cache[(fx_pair, cut_id)]
                i = data.find(ref_date, comp='le')
                return i
            return i
        except KeyError:  # data not loaded
            return None

    def _update_cache(self, all_data):
        for spot in all_data:
            self.cache[(spot.pair, spot.data_cut.cut_type)].add(spot)


# ==============

class FxBidAskForwardCurve(ForwardCurve):
    def __init__(self,
                 bid_curve: ForwardCurve,
                 mid_curve: ForwardCurve,
                 ask_curve: ForwardCurve,
                 ref_date: Date,
                 spot_date: Date,
                 dc: DayCounter = DayCounter_HD()):
        """
        An FX forward curve that includes bid, ask, and additional convenience calculations related specifically to
        FX forward curves

        :param ref_date: Date, the valuation/reference date
        :param dc: DayCounter, for measuring time
        """
        super().__init__(ref_date=ref_date, dc=dc)
        # TODO: replace with a spread curve, add the spread/2 to mid_curve to get bid/ask, else math is fucked up
        self.bid_curve = bid_curve
        self.mid_curve = mid_curve
        self.ask_curve = ask_curve
        self._spot = self.mid_curve.spot()

        self.spot_date = spot_date

    @staticmethod
    def from_linear(ttms: Union[np.ndarray, List],
                    fwds_bid: Union[np.ndarray, List],
                    fwds_mid: Union[np.ndarray, List],
                    fwds_ask: Union[np.ndarray, List],
                    ref_date: Date,
                    spot_date: Date,
                    dc: DayCounter = DayCounter_HD()) -> 'FxBidAskForwardCurve':
        """ Construct the object by linearly interpolation the bid, mid, and ask curves """
        # TODO(Justin): replace this with a mid curve and a spread curve, both linear
        bid_curve = InterpolatedForwardCurve.from_linear(ttms=ttms, forwards=fwds_bid, ref_date=ref_date, dc=dc)
        mid_curve = InterpolatedForwardCurve.from_linear(ttms=ttms, forwards=fwds_mid, ref_date=ref_date, dc=dc)
        ask_curve = InterpolatedForwardCurve.from_linear(ttms=ttms, forwards=fwds_ask, ref_date=ref_date, dc=dc)

        return FxBidAskForwardCurve(bid_curve=bid_curve, mid_curve=mid_curve, ask_curve=ask_curve,
                                    ref_date=ref_date, spot_date=spot_date, dc=dc)

    def at_T(self, T: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Evaluate the term structure at a Time in the future
        :param T: float, time in the future, T >= 0
        :return: float, the term structure evaluated at T
        """
        return self.mid_curve.at_T(T)

    def spread_at_D(self, date: Date) -> float:
        """
        Compute the bid-ask spread of the forward curve at date
        :param date: Date, the date on fwd curve
        :return: float, the bid-ask spread
        """
        return self.ask_curve.at_D(date) - self.bid_curve.at_D(date)

    def points_at_D(self, date: Date, curve_type='mid_curve') -> float:
        """
        Compute the forward points at a date
        :param date: Date, the date on fwd curve
        :return: float, the points
        """

        curve = getattr(self, curve_type)
        fwd   = curve.at_D(date)
        return (fwd - self._spot)

    def points_and_fwd_at_D(self, date: Date, curve_type='mid_curve') -> Tuple[float, float]:
        """
        Compute the forward points and the forward rate at a date
        :param date: Date, the date on fwd curve
        :return: tuple, (fwd_points, fwd_rate)
        """
        curve = getattr(self, curve_type)
        fwd   = curve.at_D(date)
        return fwd - self._spot, fwd

    def solve_points_and_fwd_from_yield_at_D(self,
                                             date: Date, spot: float, annual_yield: float
                                             ) -> Tuple[float, float]:
        """
        Solve for the implied forward points and rate given the spot and annualized (simple) yield corresponding
        to the fwd points

        :param date: Date, the date on fwd curve
        :param spot: float, the spot rate
        :param annual_yield: float, the annualized (simple) yield corresponding to the fwd points
        :return: tuple, (fwd_points, fwd_rate)
        """
        # spot * annual_yield = points / self.day_counter.year_fraction(self.spot_date, date)
        points = spot * annual_yield * self.day_counter.year_fraction(self.spot_date, date)
        fwd = spot + points
        return points, fwd

    def points_yield_at_D(self, date: Date, annualized: bool = True) -> float:
        """
        Compute the forward points at a date, with ability to convert to simple annualized or daily yield
        :param date: Date, the date on fwd curve
        :param annualized: bool, if True and as_yield = True, convert the yield to annualized
        :return: float, the yield (simple annualized or daily yield)
        """
        points = self.points_at_D(date)
        return self._convert_points_to_yield(date=date, points=points, spot=self._spot, annualized=annualized)

    def solve_spot_from_fwd_at_D(self, date: Date, fwd: float) -> float:
        """
        Solve for the spot given the forward  - solution is consistent with the current forward curve
        :param date: Date, the date on fwd curve
        :param fwd: float, the forward at the supplied date
        :return: float, the solved spot
        """
        # Log-linear Version
        # return fwd / self.at_D(date) * self._spot

        # Linear Version  (fwd = spot + pts  ->  spot = fwd - pts  )
        pts = self.points_at_D(date)
        spot = fwd - pts
        return spot

    def solve_fwd_from_spot_at_D(self, date: Date, spot: float) -> float:
        """
        Solve the fwd given the spot - solution is consistent with the current forward curve
        :param date: Date, date in the future, date >= ref_date
        :param spot: float, overide the spot
        :return: float, the term structure evaluated at date
        """
        # Log-linear Version
        # return self.at_D(date) * spot / self._spot

        # Linear Version  (fwd = spot + pts)
        pts = self.points_at_D(date)
        fwd = spot + pts
        return fwd

    @staticmethod
    def solve_points(fwd: float, spot: float) -> float:
        """
        Solve the fwd points given the fwd and spot
        :param fwd: float, the foward at some time
        :param spot: float, the spot
        :return: float, the forward points
        """
        return fwd - spot

    def solve_points_yield_at_D(self, date: Date, fwd: float, spot: float, annualized: bool = True) -> float:
        """
        Given the forward and spot, solve for the simple daily or annualized yield of the forward points

        :param fwd: float, the foward at some time
        :param spot: float, the spot
        :param date: Date, the date on fwd curve
        :param annualized: bool, if True and as_yield = True, convert the yield to annualized
        :return: float, the yield (simple annualized or daily yield)
        """
        points = fwd - spot
        return self._convert_points_to_yield(date=date, points=points, spot=spot, annualized=annualized)

    def _convert_points_to_yield(self, date: Date, points: float, spot: float, annualized: bool = True) -> float:
        points_by_spot = points / spot
        if annualized:
            return points_by_spot / self.day_counter.year_fraction(self.spot_date, date)

        return points_by_spot / self.day_counter.days_between(self.spot_date, date)


class FxForwardProvider(object):
    day_counter = DayCounter_HD()

    # DEFAULT_TENORS = ['SN','1W','2W','3W','1M','2M','3M','4M','5M','6M','9M','1Y']

    def __init__(self, fx_spot_provider: FxSpotProvider = FxSpotProvider()):
        """
        Data provider which provides FxForward data (points, forward curves, etc)
        """
        self._fx_spot_provider = fx_spot_provider

    # =====================================================================================
    #  Forward Values.
    # =====================================================================================

    def get_eod_forward_values(self, pair: FxTypes, date: Optional[Date] = None, time_as_days: bool = False):
        data_cut = DataCutService.get_eod_cut(date=date)
        return self.get_forward_values(pair=pair, date=Date.from_datetime(data_cut.cut_time),
                                       time_as_days=time_as_days)

    def get_forwards_at_time(self, fxpair: FxPair, time: Optional[Date] = None, exclude=('ON', 'TN')) -> List[
        'FxForward']:
        """
        Get the forward for an FxPair at a given time. If time doesnt match exactly, we'll find the nearest
        matching data cut
        :param fxpair: FxPair, the pair for the forward
        :param time: Date (optional), if not supplied then get latest
        :return: list of FxForward objects
        """
        if not time:
            time = Date.now()
        # Get the most recent data cut that has this fxpair
        data_cut = FxForward.objects.filter(pair=fxpair, data_cut__cut_time__lte=time) \
            .latest("data_cut__cut_time").data_cut
        return list(FxForward.objects.filter(pair=fxpair, data_cut=data_cut))

    @staticmethod
    def get_all_forward_curves(time: Optional[Date] = None,
                               spot_cache: Optional[SpotFxCache] = None,
                               dc: DayCounter = day_counter,
                               look_back_days: int = 1,
                               fx_pairs: Optional[Iterable[FxPair]] = None):

        # TODO: fix this to ignore ON/TN
        if not spot_cache and not time:
            raise ValueError(f"either a spot cache or a time must be provided")

        if not time:
            time = spot_cache.time

        if look_back_days < 1:
            raise ValueError(f"look_back_days must be at least 1 in get_all_forward_curves, was {look_back_days}")
        start_time = time - look_back_days
        timing_start = Date.now()
        params = {}
        if fx_pairs:
            params["pair__in"] = fx_pairs
        all_fx_forwards = list(FxForward.objects.select_related()
                               .filter(data_cut__cut_time__lte=time, data_cut__cut_time__gte=start_time, **params)
                               .order_by("-data_cut__cut_time"))
        timing_end = Date.now()
        logger.debug(f"  >> Got forwards from DB in {timing_end - timing_start}")

        points_by_fx = {}
        for fwd_point in all_fx_forwards:
            data = points_by_fx.setdefault(fwd_point.pair, [fwd_point.date, []])
            if data[0] < fwd_point.date:
                # Remove old data, use more recent data.
                data[0], data[1] = fwd_point.date, [fwd_point]
            elif data[0] == fwd_point.date:
                data[1].append(fwd_point)

        # At this point we have the most recent data for each FxPair that we can find within the time window.
        forwards_per_fx = {}
        for fx_pair, (date, fx_forwards) in points_by_fx.items():

            fx_spot = spot_cache.get_fx(fx_pair=fx_pair)
            if fx_spot is None:
                logger.warning(f"Could not find FX spot for {fx_pair}.")
                continue

            if not isinstance(fx_spot, float):
                fx_spot = fx_spot.rate

            times, forwards = [0.], [fx_spot]
            for fx_forward in fx_forwards:
                ttm = dc.year_fraction_from_days(fx_forward.days())
                value = fx_spot + fx_forward.fwd_points
                times.append(ttm)
                forwards.append(value)
            times = np.asarray(times)
            forwards = np.asarray(forwards)

            indx = np.argsort(times)
            times, forwards = times[indx], forwards[indx]

            fwd_curve = InterpolatedForwardCurve.from_linear(ref_date=time, dc=dc,
                                                             ttms=times,
                                                             forwards=forwards)
            forwards_per_fx[fx_pair] = fwd_curve

        return forwards_per_fx

    def get_forward_values(self,
                           pair: FxTypes,
                           date: Optional[Date] = None,
                           dc: DayCounter = day_counter,
                           time_as_days: bool = False,
                           fit: str = 'spot_points',
                           include_spot=True,
                           spot: Optional[float] = None,
                           spot_bid: Optional[float] = None,
                           spot_ask: Optional[float] = None,
                           tenors: Optional[str] = None,
                           ) -> Tuple[np.array, np.array]:
        """
        Get the forward curve for a given currency pair.

        :param pair: str, the pair id
        :param date: Date, the date on which to use the EOD data cut. Only use if data_cut is None.
        :param dc: DayCounter, the day counter used to count days along the curve
        :param time_as_days: bool, If true, return the time as days to maturity instead of year fraction
        :param spot: float, if supplied use this as the spot FX rate, else pull from spot provider
        :return: ttms and forwards, the time to maturities and forwards, as a pair of arrays
        """

        fxpair = FxPair.get_pair(pair)
        if not date:
            date = Date.now()

        forward_values = self.get_forwards_at_time(fxpair=fxpair, time=date)
        if len(forward_values) == 0:
            raise ValueError

        # filter out tenors - should be in database call
        forward_values = sorted([forward for forward in forward_values if
                                 not tenors or forward.tenor in tenors and forward.tenor not in ('ON', 'TN')],
                                key=lambda x: parse_tenor(x.tenor))

        if spot is None and fit != FIT_TYPES.POINTS:

            spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date, fxpairs=(fxpair,))

            # This pair has no forward curve data available on this date
            spot_ref = self._fx_spot_provider.get_fx(ref_date=date, fx_pair=fxpair)
            if spot_ref is None:
                raise RuntimeError(f"couldn't find fx spot in cache for {fxpair}")

            # TODO:  all sorted of parameters can go here to build better implied spots. you don't actually need spot at all.
            if isinstance(spot_ref, float):
                # this is legacy
                spot = spot_ref
            else:
                if spot is None:
                    spot = spot_ref.rate
                    # if spot_bid is None: spot_bid = spot_ref.rate_bid
                    # if spot_ask is None: spot_ask = spot_ref.rate_ask
                #else:
                    # half_spread = (spot_ref.rate_ask - spot_ref.rate_bid) / 2
                    # spot_bid = spot - half_spread
                    # spot_ask = spot + half_spread

        num_slots = len(forward_values) + 1 if include_spot else len(forward_values)
        point_days = np.ndarray((num_slots,))
        values = np.ndarray((num_slots,))

        cal = SettlementCalendar()  # TODO: source this from somewhere

        # Put the spot_date on the fwd curve as the front pillar
        pair_ = fxpair.name.replace('/', '')
        spot_date = cal.get_spot_date(pair=pair_, ref_date=date)
        spot_date = Date.from_datetime_date(spot_date)
        # spot_t = spot_date if time_as_days else dc.year_fraction(start=date, end=spot_date)

        if fit == FIT_TYPES.POINTS:
            spot = 0

        if include_spot:
            point_days[0], values[0] = 0, spot  # NOTE: puts spot at time 0
            offset = 1
        else:
            offset = 0

        for i, forward in enumerate(forward_values):

            try:
                days = cal.get_forward_days(pair=pair_, ref_date=date, tenor=forward.tenor)
            except Exception as e:
                raise Exception(f"Error getting forward days for tenor {forward.tenor}: {e}")

            t = days if time_as_days else dc.year_fraction_from_days(days=days)

            # print( forward.tenor, days, t )
            # days = forward.days()  TODO: hunt down and remove this forward.days() function
            point_days[i + offset] = t

            if fit == FIT_TYPES.POINTS:
                values[i + offset] = forward.fwd_points_ask
            elif fit == FIT_TYPES.SPOT_POINTS:
                values[i + offset] = spot + forward.fwd_points_bid
            elif fit == FIT_TYPES.OUTRIGHT:
                values[i + offset] = forward.rate_bid
            else:
                raise ValueError

        return point_days, values

    def get_forwards_bid_mid_ask(self,
                                 pair: FxTypes,
                                 date: Optional[Date] = None,
                                 dc: DayCounter = day_counter,
                                 time_as_days: bool = False,
                                 fit: str = 'spot_points',
                                 include_spot=True,
                                 spot: Optional[float] = None,
                                 spot_bid: Optional[float] = None,
                                 spot_ask: Optional[float] = None,
                                 tenors: Optional[str] = None,
                                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Date]:
        """
        Get the forward curve for a given currency pair.

        :param pair: str, the pair id
        :param date: Date, the date on which to use the EOD data cut. Only use if data_cut is None.
        :param dc: DayCounter, the day counter used to count days along the curve
        :param time_as_days: bool, If true, return the time as days to maturity instead of year fraction
        :param spot: float, if supplied use this as the spot FX rate, else pull from spot provider
        :return: ttms and forwards, the time to maturities and forwards, as follows: (ttms, bids, mids, asks, Date),
            the final element in tuple is the spot date of the forward curve
        """

        fxpair = FxPair.get_pair(pair)
        if not date:
            date = Date.now()

        forward_values = self.get_forwards_at_time(fxpair=fxpair, time=date)
        if len(forward_values) == 0:
            raise ValueError

        # filter out tenors - should be in database call
        forward_values = sorted([forward for forward in forward_values if
                                 not tenors or forward.tenor in tenors and forward.tenor not in ('ON', 'TN')],
                                key=lambda x: parse_tenor(x.tenor))

        if None in (spot, spot_bid, spot_ask) and fit != FIT_TYPES.POINTS:
            spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date, fxpairs=(fxpair,))

            # This pair has no forward curve data available on this date
            spot_ref = self._fx_spot_provider.get_fx(ref_date=date, fx_pair=fxpair)
            if spot_ref is None:
                raise RuntimeError(f"couldn't find fx spot in cache for {fxpair}")

            if isinstance(spot_ref, float):
                # this is legacy
                spot = spot_ref
                if spot_bid is None: spot_bid = spot_ref
                if spot_ask is None: spot_ask = spot_ref
            else:
                # TODO:  all sorted of parameters can go here to build better implied spots. you don't actually need spot at all.
                if spot is None:
                    spot = spot_ref.rate
                    if spot_bid is None: spot_bid = spot_ref.rate_bid
                    if spot_ask is None: spot_ask = spot_ref.rate_ask
                else:
                    half_spread = (spot_ref.rate_ask - spot_ref.rate_bid) / 2
                    spot_bid = spot - half_spread
                    spot_ask = spot + half_spread

        num_slots = len(forward_values) + 1 if include_spot else len(forward_values)
        point_days = np.ndarray((num_slots,))
        bids = np.ndarray((num_slots,))
        mids = np.ndarray((num_slots,))
        asks = np.ndarray((num_slots,))

        cal = SettlementCalendar()  # TODO: source this from somewhere

        # Put the spot_date on the fwd curve as the front pillar
        pair_ = fxpair.name.replace('/', '')
        spot_date = cal.get_spot_date(pair=pair_, ref_date=date)
        spot_date = Date.from_datetime_date(spot_date)
        # spot_t = spot_date if time_as_days else dc.year_fraction(start=date, end=spot_date)

        if fit == FIT_TYPES.POINTS:
            spot, spot_bid, spot_ask = 0, 0, 0
        else:
            if not spot_bid:
                spot_bid = spot
            if not spot_ask:
                spot_ask = spot

        if include_spot:
            point_days[0], bids[0], mids[0], asks[0] = 0, spot_bid, spot, spot_ask  # NOTE: puts spot at time 0
            offset = 1
        else:
            offset = 0

        for i, forward in enumerate(forward_values):

            try:
                days = cal.get_forward_days(pair=pair_, ref_date=date, tenor=forward.tenor)
            except Exception as e:
                raise Exception(f"Error getting forward days for {fxpair.market} tenor {forward.tenor} at {str(date)}: {e}")

            t = days if time_as_days else dc.year_fraction_from_days(days=days)

            # print( forward.tenor, days, t )
            # days = forward.days()  TODO: hunt down and remove this forward.days() function
            point_days[i + offset] = t

            if fit == FIT_TYPES.POINTS:
                bids[i + offset] = forward.fwd_points_bid
                mids[i + offset] = forward.fwd_points
                asks[i + offset] = forward.fwd_points_ask
            elif fit == FIT_TYPES.SPOT_POINTS:
                bids[i + offset] = spot + forward.fwd_points_bid
                mids[i + offset] = spot + forward.fwd_points
                asks[i + offset] = spot + forward.fwd_points_ask
            elif fit == FIT_TYPES.OUTRIGHT:
                bids[i + offset] = forward.rate_bid
                mids[i + offset] = forward.rate
                asks[i + offset] = forward.rate_ask
            else:
                raise ValueError

        return point_days, bids, mids, asks, spot_date

    # =====================================================================================
    #  Forward curves.
    # =====================================================================================

    def get_forward_curve(self,
                          pair: FxTypes,
                          date: Optional[Date] = None,
                          dc: DayCounter = day_counter,
                          spot: Optional[float] = None,
                          tenors: Optional[list] = None,
                          interp: str = INTERP_TYPES.LINEAR) -> ForwardCurve:
        """
        Get the forward curve for a given currency pair.

        :param pair: str, the pair id
        :param date: Optional[Date], the date on which to use the EOD data cut. Only use if data_cut is None.
        :param dc: DayCounter, the day counter used to count days along the curve
        :param spot: float, if supplied use this as the spot FX rate, else pull from spot provider
        :return: ForwardCurve, object
        """
        if not date:
            date = Date.now()
        times, forwards = self.get_forward_values(pair=pair, date=date, dc=dc, spot=spot, tenors=tenors)

        if interp == INTERP_TYPES.LINEAR:
            return InterpolatedForwardCurve.from_linear(ttms=times,
                                                        forwards=forwards,
                                                        ref_date=date, dc=dc)
        else:
            raise ValueError

    def get_forward_bid_ask_curve(self,
                                  pair: FxTypes,
                                  date: Optional[Date] = None,
                                  dc: DayCounter = day_counter,
                                  spot: Optional[float] = None,
                                  tenors: Optional[list] = None,
                                  interp: str = INTERP_TYPES.LINEAR) -> FxBidAskForwardCurve:
        """
        Get the FxBidAskForwardCurve object for a given currency pair.

        :param pair: str, the pair id
        :param date: Optional[Date], the date on which to use the EOD data cut. Only use if data_cut is None.
        :param dc: DayCounter, the day counter used to count days along the curve
        :param spot: float, if supplied use this as the spot FX rate, else pull from spot provider
        :return: FxBidAskForwardCurve, object
        """
        if not date:
            date = Date.now()
        times, bids, mids, asks, spot_date = self.get_forwards_bid_mid_ask(pair=pair, date=date, dc=dc, spot=spot,
                                                                           tenors=tenors)

        if interp == INTERP_TYPES.LINEAR:
            return FxBidAskForwardCurve.from_linear(ttms=times,
                                                    fwds_ask=asks, fwds_mid=mids, fwds_bid=bids,
                                                    ref_date=date, spot_date=spot_date, dc=dc)
        else:
            raise ValueError

    # noinspection DuplicatedCode
    @staticmethod
    def get_most_recent_forward_curves(pairs: Sequence[FxPair],
                                       time: Optional[Date] = None,
                                       dc: DayCounter = day_counter,
                                       spot_cache: Optional[SpotFxCache] = None,
                                       window: int = 14
                                       ) -> Tuple[Dict[FxPair, Optional[ForwardCurve]],
                                                  Dict[FxPair, Optional[Date]]]:
        # TODO
        raise NotImplementedError

        if time is None:
            time = Date.now()
        min_time = time - window

        objects = FxForward.objects.filter(pair__in=pairs,
                                           data_cut__cut_time__lte=time,
                                           data_cut__cut_time__gte=min_time)

        most_recent_dates, forwards = {}, {}
        for fwds in objects:
            date = fwds.data_time
            pair = fwds.pair
            if pair not in most_recent_dates or most_recent_dates[pair] < date:
                most_recent_dates[pair] = date
                forwards[pair] = []
            if most_recent_dates[pair] == date:
                forwards[pair].append(fwds)

        # Get Fx spots.
        if spot_cache is None:
            spot_cache = FxSpotProvider().get_spot_cache(time=time, fxpairs=pairs, window=window)

        output, actual_date = {}, {}
        for pair in pairs:
            # If we didn't find any forward data for a pair, we will try to create a flat forward curve.
            entries: List[FxForward] = forwards.get(pair, [])

            ttms = np.zeros(len(entries) + 1)
            fwds = np.zeros(len(entries) + 1)

            spot = spot_cache.get_fx(pair, None)
            if spot is None:
                # If spot is none, we can't even create a flat forward curve. Return None.
                output[pair] = None
                actual_date[pair] = None
                continue
            if len(entries) == 0:
                # If we only have spot, create a flat forward curve.
                output[pair] = FlatForwardCurve(F0=spot, ref_date=time, dc=dc)
                actual_date[pair] = None
                continue

            ttms[0] = 0.
            fwds[0] = spot if isinstance(spot, float) else spot.rate

            for it, obj in enumerate(sorted(entries, key=lambda x: x.days())):
                ttms[it + 1] = dc.year_fraction_from_days(obj.days())
                fwds[it + 1] = spot + obj.fwd_points

            actual_date[pair] = Date.from_datetime(most_recent_dates[pair])
            output[pair] = InterpolatedForwardCurve.from_linear(ttms=ttms,
                                                                forwards=fwds,
                                                                ref_date=time,
                                                                dc=dc)

        return output, actual_date


class FxVolAndCorrelationProvider(object):
    """
    Data service which provides Fx spot volatility and correlation data
    """
    day_counter = DayCounter_HD()

    def __init__(self,
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 fx_forward_provider: FxForwardProvider = FxForwardProvider()):
        self._fx_spot_provider = fx_spot_provider
        self._fx_forward_provider = fx_forward_provider

    # =====================================================================================
    #  Spot Volatilities
    # =====================================================================================

    def get_vols(self,
                 pairs: Sequence[Union[FxPair, FxPairId]],
                 data_cut: DataCut,
                 estimator: FxEstimatorTypes = "Covar-Prod") -> Sequence['FxSpotVol']:
        # TODO: deprecate in favor of get_vols_at_time
        return FxSpotVol.objects.filter(pair__in=pairs, data_cut=data_cut,
                                        estimator=FxEstimator.get_estimator(estimator))

    def get_vols_at_time(self,
                         pairs: Optional[Sequence[Union[FxPair, FxPairId]]] = None,
                         time: Optional[Date] = None,
                         estimator: FxEstimatorTypes = "Covar-Prod") -> Tuple[Sequence['FxSpotVol'], DataCut]:
        if not time:
            time = Date.now()
        data_cut = FxSpotVol.objects.select_related().filter(estimator=estimator, data_cut__cut_time__lte=time) \
            .latest("data_cut__cut_time").data_cut

        qs = FxSpotVol.objects.filter(data_cut=data_cut,
                                      estimator=FxEstimator.get_estimator(estimator))
        if pairs:
            qs = qs.filter(pair__in=pairs)
        return qs, data_cut

    def get_spot_vols(self,
                      data_cut: DataCut,
                      pairs: Sequence[FxPair] = None,
                      pair_ids: Sequence[FxPairId] = None,
                      estimator: FxEstimatorTypes = "Covar-Prod") -> Dict[FxPairName, float]:
        # TODO: deprecate in favor of get_spot_vols_at_time
        if pairs is None or len(pairs) == 0:
            pairs = FxPair.get_pairs(pair_ids=pair_ids)

        return self.get_vol_map(pairs=pairs, data_cut=data_cut, estimator=estimator)

    def get_spot_vols_at_time(self,
                              time: Optional[Date] = None,
                              pairs: Sequence[FxPair] = None,
                              pair_ids: Sequence[FxPairId] = None,
                              estimator: FxEstimatorTypes = "Covar-Prod") -> Dict[FxPair, float]:
        if pairs is None or len(pairs) == 0:
            pairs = FxPair.get_pairs(pair_ids=pair_ids)

        return self.get_vol_map_at_time(pairs=pairs, time=time, estimator=estimator)

    def get_vol_map(self,
                    pairs: Sequence[FxPair],
                    data_cut: DataCut,
                    estimator: FxEstimatorTypes = "Covar-Prod") -> Dict[FxPairName, float]:
        """
        Get volatilies for fx pairs
        :param pairs: Sequence of FxPairs or their ids
        :param data_cut: DataCut, the data cut
        :param estimator: int, the estimator
        :return: Dictionary from name of FxPair to its vol
        """
        # TODO: deprecate in favor of get_vol_map_at_time
        estimator_ = FxEstimator.get_estimator(estimator)
        vols = self.get_vols(pairs=pairs, data_cut=data_cut, estimator=estimator_)

        vols_out = {}
        for fxSpotVol in vols:
            vols_out[fxSpotVol.pair_name] = fxSpotVol.vol

        # Try to get the vol for the inverse pair (which is the same under log return assumption)
        if len(vols) != len(pairs):
            for pair in pairs:
                if pair.name not in vols_out:
                    try:
                        fxSpotVol = FxSpotVol.objects.get(pair=pair.get_inverse_pair(pair=pair),
                                                          data_cut=data_cut, estimator=estimator_)
                        if fxSpotVol is not None:
                            vols_out[pair.name] = fxSpotVol.vol
                    except Exception as e:
                        # Unable to load this vol... will not be available later if its needed
                        pass
        return vols_out

    def get_vol_map_at_time(self,
                            pairs: Sequence[FxPair],
                            time: Optional[Date] = None,
                            estimator: FxEstimatorTypes = "Covar-Prod") -> Dict[FxPair, float]:
        """
        Get volatilies for fx pairs
        :param pairs: Sequence of FxPairs or their ids
        :param estimator: int, the estimator
        :return: Dictionary from name of FxPair to its vol
        """
        estimator_ = FxEstimator.get_estimator(estimator)
        vols, data_cut = self.get_vols_at_time(pairs=None, time=time, estimator=estimator_)

        vols_out = {}
        for fx_spot_vol in vols:
            vols_out[fx_spot_vol.pair] = fx_spot_vol.vol

        return vols_out

    # =====================================================================================
    #  Spot Vol Time Series
    # =====================================================================================

    def get_time_series(self,
                        fxpair: Union[FxPair, FxPairId],
                        estimator: FxEstimatorTypes = "Covar-Prod") -> List[Tuple[Date, float]]:
        data = FxSpotVol.objects.filter(pair=FxPair.get_pair(fxpair), estimator=FxEstimator.get_estimator(estimator)) \
            .order_by("data_cut__cut_time")

        output = []
        for point in data:
            output.append((Date.to_date(point.date), point.vol))
        return output

    # =====================================================================================
    #  Spot Correlations
    # =====================================================================================

    def get_spot_correl_matrix(self,
                               data_cut: DataCut,
                               pairs: Sequence[FxPair] = None,
                               estimator: FxEstimatorTypes = "Covar-Prod") -> pd.DataFrame:
        """
        Get spot correlation matrix (instantaneous correlations of movements in log space)
        :param data_cut: DataCut, the data cut to retrive data
        :param pairs: sequence of FxPair objs (optional), which pairs to get correlations for.. supply this or
            pair_ids
        :param estimator: which estimator we look up for the correlations (e.g. EWMA)
        :return: pd.DataFrame, a matrix of spot correlations between fx pairs
        """

        estimator_ = FxEstimator.get_estimator(estimator)
        if not estimator_:
            raise ValueError(f"could not find estimator {estimator}")

        correl_matrix = FxSpotCovariance.get_correlation_matrix(pairs=pairs, data_cut=data_cut,
                                                                estimator=estimator_)

        # Convert to a dataframe, because, unfortunately, we are forced to store correlation in a dataframe.
        pair_names = [pair.name for pair in pairs]  # get names of pairs to put into matrix
        index = {i: str(pair) for i, pair in enumerate(pairs)}

        num_pairs = len(pairs)
        df = pd.DataFrame(index=pair_names, columns=pair_names, dtype=float)
        for i in range(num_pairs):
            for j in range(num_pairs):
                df.loc[index[i], index[j]] = correl_matrix[i, j]
        return df

    def _get_intercorrelations(self,
                               pairs: Sequence[FxPair],
                               data_cut: DataCut,
                               estimator: FxEstimatorTypes) -> List[Tuple[FxPair, FxPair, float]]:
        """
        Get correlations where both pairs are in the list of specified pairs. This only returns the OFF diagonals,
        it doesnt include correlations of 1 between FxPair and itself
        """
        if len(pairs) == 0:
            return []

        out = []
        for i in range(len(pairs)):
            pair1 = pairs[i]
            for j in range(i):
                pair2 = pairs[j]
                rho = FxSpotCovariance.get_correlation(pair_1=pair1, pair_2=pair2, data_cut=data_cut,
                                                       estimator=estimator)
                if rho is None:
                    rho = np.nan
                out.append((pair1, pair2, rho))

        return out


# =============

class ForwardImpliedDiscountCurve(DiscountCurve):
    def __init__(self,
                 forward_curve: FxBidAskForwardCurve,
                 quote_depo: DiscountCurve,
                 shift_forward_curve_to_spot: bool = True
                 ):
        """
        Implied discount curve given a forward curve and depo/discount curve for quote currency
        Assumption: F(T) = FX_0 * Disc_f(T) / Disc_d(T)  => Disc_f(T) = F(T) / FX_0 * Disc_d(T)

        :param forward_curve: ForwardCurve, the forward curve for BASE/QUOTE (we will imply BASE discounts)
        :param quote_depo: DiscountCurve, the depo curve for the quote currency (ie domestic or counter currency)
        """
        super().__init__(ref_date=forward_curve.ref_date, dc=forward_curve.day_counter)
        self._quote_depo = quote_depo
        self._forward_curve = forward_curve
        self._shift_forward_curve_to_spot = shift_forward_curve_to_spot

    def at_T(self, T: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Discount at time T in the future
        :param T: float or np.ndarray, time(s) in the future
        :return: float or np.ndarray, discounts(s) at time(s) in the future
        """
        if self._shift_forward_curve_to_spot:
            t_subtract = min(T,
                             self._forward_curve.day_counter.year_fraction(self.ref_date,
                                                                           self._forward_curve.spot_date))
        else:
            t_subtract = 0
        return self._forward_curve.at_T(T - t_subtract) / self._forward_curve.spot() * self._quote_depo.at_T(T)
