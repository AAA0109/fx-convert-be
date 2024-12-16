import logging
from abc import ABC
from typing import List, Union, Sequence, Optional, Set, Iterable, Callable

import numpy as np
import pandas as pd
from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD, DayCounter
from hdlib.TermStructures.TermStructure import TermStructure
from scipy.interpolate import interp1d

from main.apps.currency.models.fxpair import FxPair, FxPairTypes
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.models.fx.option import FxOptionStrategy
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.support.TenorConverter import TenorConverter

logger = logging.getLogger(__name__)


class OptionStrategyContainer(object):
    def __init__(self,
                 fx_pair: FxPair,
                 data_cut: DataCut,
                 strats: Sequence[FxOptionStrategy]):
        self.fx_pair = fx_pair
        self.data_cut = data_cut

        rows = []
        self._tenors = set()

        for strat in strats:
            df = strat.get_df(pair_id=strat.pair.pk, data_cut_id=strat.data_cut.pk)
            for _, row in df.iterrows():

                days = TenorConverter().get_days_from_tenor(tenor=row['tenor'], fx_pair_name=strat.pair.name)

                if days > 0:
                    self._tenors.add(row['tenor'])

                    bid_value = row.get('bid_value', np.nan)
                    ask_value = row.get('ask_value', np.nan)

                    rows.append((
                        row['tenor'],
                        days,
                        row['name'],
                        row['strategy'],
                        row['offset'],
                        bid_value,
                        ask_value,
                        row['mid_value']
                    ))

        self._df = pd.DataFrame(data=rows, columns=['tenor', 'days', 'name', 'strategy', 'offset',
                                                    'bid_value', 'ask_value', 'mid_value'])

    def __len__(self) -> int:
        return len(self._tenors)

    @property
    def date(self) -> Date:
        return self.data_cut.date

    @property
    def tenors(self) -> Set[str]:
        return self._tenors

    @property
    def frame(self) -> pd.DataFrame:
        return self._df

    def get_strats_for_tenor(self, tenor: str) -> pd.DataFrame:
        return self._df[self._df['tenor'] == tenor]

    def get_atms(self, sort: bool = True) -> pd.Series:
        df_atm = self._df[self._df['offset'] == '0']
        if sort:
            df_atm.sort_values('days', inplace=True)
        return pd.Series(data=df_atm['mid_value'].values, index=df_atm['days'].values)


class AtmVolTermStructure(TermStructure, ABC):
    """
     Base class for ATM (at-the-money) volatility term structures. This represents the backbone of the vol
     surface as a function of time
    """
    pass


class ConstantAtmVolTermStructure(AtmVolTermStructure):

    def __init__(self,
                 vol: float,
                 ref_date: Date,
                 dc: DayCounter = DayCounter_HD()):
        super(ConstantAtmVolTermStructure, self).__init__(ref_date=ref_date, dc=dc)
        self._vol = vol

    def at_T(self, T: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Evaluate the term structure at a Time in the future
        :param T: float, time in the future, T >= 0
        :return: float, the term structure evaluated at T
        """
        return self._vol


class InterpolatedAtmVolTermStructure(AtmVolTermStructure):

    def __init__(self,
                 interp: Callable,
                 ref_date: Date,
                 dc: DayCounter = DayCounter_HD()):
        super(InterpolatedAtmVolTermStructure, self).__init__(ref_date=ref_date, dc=dc)
        self._interp = interp  # interpolation of total variance
        self._min_ttm = 1 / 365.

    def at_T(self, T: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Evaluate the term structure at a Time in the future
        :param T: float, time in the future, T >= 0
        :return: float, the term structure evaluated at T
        """
        t = np.maximum(self._min_ttm, T)
        return np.sqrt(self._interp(t) / t)

    @classmethod
    def from_linear(cls,
                    dtms: Union[np.ndarray, List],
                    vols: Union[np.ndarray, List],
                    ref_date: Date,
                    dc: DayCounter = DayCounter_HD()) -> 'InterpolatedAtmVolTermStructure':
        """
        Convenience method to construct a linearly interpolated atm vol term structure
        :param dtms: array-like, the x-points, correspond to tenors (days to maturity)
        :param vols: array-like, the y-points, correspond to atm implied volatilities
        :param ref_date: Date, the valuation/reference date
        :param dc: DayCounter, for measuring time
        :return: AtmVolTermStructure, interpolation of points and values
        """
        if dtms[0] > 1:
            dtms = np.append(1, dtms)
            vols = np.append(vols[0], vols)
        ttms = np.array([dc.year_fraction_from_days(days) for days in dtms])

        vols = np.power(vols, 2) * ttms
        interp = interp1d(ttms, vols, fill_value='extrapolate', bounds_error=False)
        return cls(interp=interp, ref_date=ref_date, dc=dc)


class FxOptionStrategyProvider(object):
    """
    Market Data FX Provider class, provides methods to retrieve options strategies data
    """
    day_counter = DayCounter_HD()

    def __init__(self):
        pass

    def get_strategies_for_pair(self,
                                fxpair: FxPairTypes,
                                date: Optional[Date] = None,
                                data_cut: Optional[DataCut] = None,
                                latest_available: bool = False) -> Sequence[FxOptionStrategy]:
        """
        Get option strategies objects for a given pair and date
        :param fxpair: FxPairTypes, which pair to get
        :param date: Optional[Date], if supplied will look for a datacut on this date (see latest_available)
        :param data_cut: Optional[DataCut], if supplied will pull the data for exactly this cut if it is found
        :param latest_available: bool, if supplied with date, it will find the latest available data cut up
            to and including that date. Else, the data must exist on exactly the date supplied
        :return: Sequence[FxOptionStrategy], the strategies for a single pair on a single date
        """
        data_cut = self._get_data_cut(date=date, data_cut=data_cut, latest_available=latest_available)
        fxpair_ = FxPair.get_pair(fxpair)
        if not fxpair_:
            raise FxPair.DoesNotExist(f"Couldnt find the fx pair: {fxpair}")

        return FxOptionStrategy.objects.filter(data_cut=data_cut, pair=fxpair_)

    def get_strategies_container_for_pair(self,
                                          fxpair: FxPairTypes,
                                          date: Optional[Date] = None,
                                          data_cut: Optional[DataCut] = None,
                                          latest_available: bool = False
                                          ) -> OptionStrategyContainer:
        data_cut = self._get_data_cut(date=date, data_cut=data_cut, latest_available=latest_available)
        fxpair_ = FxPair.get_pair(fxpair)
        if not fxpair_:
            raise FxPair.DoesNotExist(f"Couldnt find the fx pair: {fxpair}")

        return OptionStrategyContainer(fx_pair=fxpair_, data_cut=data_cut,
                                       strats=self.get_strategies_for_pair(fxpair=fxpair_,
                                                                           data_cut=data_cut))

    def get_strategy_time_series_for_pair(self,
                                          fx_pair: FxPairTypes,
                                          min_date: Date = None,
                                          max_date: Date = None,
                                          strategies: Iterable[str] = None,
                                          tenors: Iterable[str] = None) -> pd.DataFrame:
        filters = {"pair": FxPair.get_pair(fx_pair)}
        if min_date:
            filters['data_cut__cut_time__gte'] = min_date
        if max_date:
            filters['data_cut__cut_time__lte'] = max_date
        if strategies is not None:
            filters['strategy__in'] = strategies
        if tenors is not None:
            filters['tenor__in'] = tenors

        data = FxOptionStrategy.objects.filter(**filters).order_by("data_cut__cut_time")

        output = []
        for fx_option_strategy in data:
            df = fx_option_strategy.get_df(pair_id=fx_option_strategy.pair.pk,
                                           data_cut_id=fx_option_strategy.data_cut.pk)
            for _, row in df.iterrows():
                output.append((
                    pd.to_datetime(row['date']),
                    row['mid_value'],
                    row['name'],
                    row['strategy'],
                    row['tenor'],
                    row['offset']
                ))

        df = pd.DataFrame(data=output, columns=['date', 'mid_value', 'name', 'strategy', 'tenor', 'offset'])
        df.sort_values('date', inplace=True)
        return df

    def get_atm_vols_for_pairs_on_date(self,
                                       date: Optional[Date] = None,
                                       data_cut: Optional[DataCut] = None,
                                       fx_pairs: Optional[Iterable[FxPair]] = None,
                                       latest_available: bool = False) -> pd.DataFrame:
        """
        Get option strategies objects for fx pair(s) on single date
        :param fx_pairs: Optional[Iterable[FxPair]], if not supplied then pull all available pairs
        :param date: Optional[Date], if supplied will look for a datacut on this date (see latest_available)
        :param data_cut: Optional[DataCut], if supplied will pull the data for exactly this cut if it is found
        :param latest_available: bool, if supplied with date, it will find the latest available data cut up
            to and including that date. Else, the data must exist on exactly the date supplied
        :return: pd.DataFrame, contains the strategies for on a single date for all pairs requested
        """
        data_cut = self._get_data_cut(date=date, data_cut=data_cut, latest_available=latest_available,
                                      fx_pairs=fx_pairs)
        filters = {'data_cut': data_cut,
                   'offset': '0'}
        if fx_pairs:
            filters['pair__in'] = fx_pairs

        data = FxOptionStrategy.objects.filter(**filters).order_by("pair")

        output = []
        for fx_option_strategy in data:
            df = fx_option_strategy.get_df(pair_id=fx_option_strategy.pair.pk,
                                           data_cut_id=fx_option_strategy.data_cut.pk)
            for _, row in df.iterrows():
                if row['mid_value'] <= 0:
                    continue

                output.append((
                    fx_option_strategy.pair.id,
                    pd.to_datetime(row['date']),
                    row['tenor'],
                    TenorConverter().get_days_from_tenor(tenor=row['tenor'],
                                                         fx_pair_name=fx_option_strategy.pair.name),
                    row['mid_value'] / 100,
                ))

        df = pd.DataFrame(data=output, columns=['pair', 'date', 'tenor', 'dtm', 'mid_value'])
        df.sort_values(['pair', 'dtm'], inplace=True)

        return df

    def _get_data_cut(self,
                      date: Optional[Date] = None,
                      data_cut: Optional[DataCut] = None,
                      latest_available: bool = False,
                      fx_pairs: Optional[Iterable[FxPair]] = None,
                      max_days_back: int = 7
                      ):
        if not data_cut:
            if not date:
                raise ValueError("You must supply either a date or a data cut")
            if latest_available:
                filters = {}
                if fx_pairs:
                    filters['pair__in'] = fx_pairs
                    d = Date.to_date(date)
                    filters['data_cut__cut_time__lte'] = d
                    filters['data_cut__cut_time__gte'] = d - max_days_back  # Dont all to go back more than this

                fx_option_strategy = FxOptionStrategy.objects.filter(**filters).order_by("-acquired_date").first()

                if fx_option_strategy:
                    df = fx_option_strategy.get_df(pair_id=fx_option_strategy.pair.pk,
                                           data_cut_id=fx_option_strategy.data_cut.pk)
                    if not df.empty:
                        # Assuming the CSV has a 'data_cut' column
                        latest_data_cut_time = pd.to_datetime(df['data_cut'].iloc[0])
                        return DataCut.objects.filter(cut_time=latest_data_cut_time).first()

            return DataCutService.get_eod_cut(date)
        return data_cut
