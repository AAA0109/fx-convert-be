import datetime
import numpy as np
import pandas as pd
from django.db import models

from main.apps.marketdata.models.marketdata import MarketData, DataCut
from main.apps.currency.models import FxPair, FxPairId, FxPairName, FxPairTypes
from main.apps.util import get_or_none, ActionStatus
from . import Fx

from hdlib.DateTime.Date import Date
from hdlib.Core.FxPair import FxPair as FxPairHDL

from typing import List, Dict, Union, Iterable, Optional, Sequence, Tuple

import logging

logger = logging.getLogger(__name__)

# =====================================
# Type Definitions
# =====================================
FxEstimatorId = int


class FxEstimator(models.Model):
    """
    FX Estimators (e.g. vol, correlation, etc). This is used to keep a record of which estimator was used to
    obtain certain modeled data, and to allow new estimators to cleanly replace old ones over time.
    """

    class Meta:
        unique_together = (("tag",),)

    class EstimatorType(models.IntegerChoices):
        EWMA = 1  # Ewma Estimate
        GAS = 2  # GAS Estimator (for volatility), see e.g. http://www.gasmodel.com/
        ML = 3  # Machine Learning (for volatility)

    type = models.IntegerField(null=False, default=EstimatorType.EWMA, choices=EstimatorType.choices)
    tag = models.CharField(max_length=255, null=False)  # Some readable identifier, e.g. 'EWMA Vol Estimator'
    parameters = models.CharField(max_length=255, null=True)  # Store a record of which paramaters where used

    def __str__(self):
        return self.tag

    @staticmethod
    @get_or_none
    def get_estimator(estimator: Union[FxEstimatorId, 'FxEstimator', str]) -> Optional['FxEstimator']:
        if isinstance(estimator, str):
            return FxEstimator.objects.get(tag=estimator)
        if isinstance(estimator, FxEstimatorId):
            return FxEstimator.objects.get(id=estimator)
        if isinstance(estimator, FxEstimator):
            return estimator
        return None

    @staticmethod
    @get_or_none
    def get_estimator_by_tag(tag: str):
        return FxEstimator.objects.get(tag=tag)

    def estimate(self,
                 value_topday: float,
                 estimator_lastday: float,
                 date_topday: Optional[Date] = None,
                 date_lastday: Optional[Date] = None):
        if self.type == FxEstimator.EstimatorType.EWMA:
            lam = float(self.parameters)
            return (1. - lam) * value_topday + lam * estimator_lastday

        if self.type == FxEstimator.EstimatorType.GAS:
            # q = Student-T inverse number of degrees of freedom.
            l, q = self.parameters.split(":")
            lam, q = float(l), float(q)

            num = (1 + q) * value_topday
            den = (1 - 2 * q) * (1 + q * value_topday / ((1 - 2 * q) * estimator_lastday))

            return estimator_lastday + (1 - lam) * (1 + 3 * q) * (num / den - estimator_lastday)

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def create_estimator(type: EstimatorType,
                         tag: str,
                         parameters: Union[str, float]) -> Tuple[ActionStatus, 'FxEstimator']:
        if isinstance(parameters, float):
            parameters = str(parameters)
        estimator, created = FxEstimator.objects.get_or_create(type=type, tag=tag, parameters=parameters)
        if not created:
            return ActionStatus.no_change(f"Estimator already exists"), estimator

        return ActionStatus.success(f"Created estimator {tag}"), estimator


# The types that can denote an Fx estimator.
FxEstimatorTypes = Union[FxEstimatorId, FxEstimator, str]


# ==================================
# Historical Volatility Estimator
# ==================================


class FxSpotVol(Fx):
    """
    Historical Vol Estimate for FX Spot
    """
    vol = models.FloatField(null=False)
    estimator = models.ForeignKey(FxEstimator, on_delete=models.CASCADE, null=False)

    class Meta:
        unique_together = (("data_cut", "pair", "estimator"),)

    @property
    def pair_name(self) -> str:
        return self.pair.name

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_spot_vol_ts(fxpair: FxPairTypes,
                        estimator: FxEstimatorTypes,
                        start_date: Optional[Date] = None,
                        end_date: Optional[Date] = None) -> Tuple[np.array, np.array]:
        fxpair_ = FxPair.get_pair(fxpair)
        if fxpair_ is None:
            raise RuntimeError(f"could not find FxPair from {fxpair}")

        estimator_ = FxEstimator.get_estimator(estimator)
        if estimator_ is None:
            raise RuntimeError(f"cannot find estimator from {estimator}")

        filters = {"pair": fxpair_, "estimator": estimator_}
        if start_date:
            filters["data_cut__cut_time__gte"] = start_date
        if end_date:
            filters["data_cut__cut_time__lte"] = end_date

        vol_objects = FxSpotVol.objects.filter(**filters).order_by("data_cut__cut_time")
        times, vols = [], []
        for vol in vol_objects:
            times.append(vol.data_cut.cut_time)
            vols.append(vol.vol)

        return np.array(times), np.array(vols)

    @staticmethod
    def get_spot_vol(fxpair: FxPairTypes, estimator: FxEstimatorTypes, date: Date) -> Optional[Tuple[float, Date]]:
        fxpair = FxPair.get_pair(fxpair)
        estimator = FxEstimator.get_estimator(estimator)

        # Get the most recent spot vol for each pair at a time not greater than "date"
        spot_vol = FxSpotVol.objects \
            .filter(date__lte=date, pair=fxpair, estimator=estimator) \
            .order_by("-date") \
            .first()
        if spot_vol:
            return spot_vol.vol, Date.from_datetime(spot_vol.date)
        return None

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def add_spot_vol(fxpair: FxPairTypes,
                     data_cut: DataCut,
                     estimator: FxEstimator,
                     vol: float,
                     update: bool = False) -> Tuple[ActionStatus, Optional['FxSpotVol']]:
        fxpair = FxPair.get_pair(fxpair)
        try:
            try:
                spot_vol = FxSpotVol.objects.get(data_cut=data_cut, pair=FxPair.get_pair(fxpair), estimator=estimator)
                if update:
                    spot_vol.vol = vol
                    spot_vol.save()
                    return ActionStatus.success(f"Updated spot vol"), spot_vol
            except FxSpotVol.DoesNotExist:
                spot_vol = FxSpotVol.objects.create(date=data_cut.date,
                                                    data_cut=data_cut,
                                                    pair=FxPair.get_pair(fxpair),
                                                    estimator=estimator,
                                                    vol=vol)
                return ActionStatus.success(f"Added spot vol, cut {data_cut} for pair {fxpair}, value = {vol}"), \
                       spot_vol
        except Exception as ex:
            return ActionStatus.error(f"Could not add spot vol: {ex}"), None
        return ActionStatus.no_change(f"Spot vol already added"), spot_vol


# ==================================
# Covariance Estimator
# ==================================

class FxSpotCovariance(MarketData):
    """
    Historical cross-volatility Estimate for FX Spot pairs
    """
    pair_1 = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False, related_name="cross_vol_pair_1")
    pair_2 = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False, related_name="cross_vol_pair_2")
    covariance = models.FloatField(null=False)
    estimator = models.ForeignKey(FxEstimator, on_delete=models.CASCADE, null=False)

    class Meta:
        unique_together = (("data_cut", "pair_1", "pair_2", "estimator"),)

    # TODO: Finish moving the accessors out of this class and into the service (FxSpotVolAndCorrelationProvider)

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def has_covariance(fxpair1: FxPairTypes, fxpair2: FxPairTypes, estimator: FxEstimatorTypes) -> bool:
        """
        Check if there are any spot covariances for a pair and estimator.
        """
        fxpair1_, fxpair2_ = FxPair.get_pair(fxpair1), FxPair.get_pair(fxpair2)
        if fxpair1_ is None or fxpair2_ is None:
            raise RuntimeError(f"one or more of the FX pairs do not exist")
        return 0 < len(FxSpotCovariance.objects.filter(pair_1=fxpair1_, pair_2=fxpair2_, estimator=estimator))

    @staticmethod
    @get_or_none
    def get_covariance(pair_1: FxPairTypes,
                       pair_2: FxPairTypes,
                       data_cut: DataCut,
                       estimator: FxEstimatorTypes) -> Optional[float]:
        """
        Get the cross vol between two fx pairs on a date
        :param pair_1: first FxPair
        :param pair_2: second FxPair
        :param data_cut: DataCut, the data cut for the correlation estimate
        :param estimator: the estimator id
        :return: float, the cross vol between pairs on this date
        """
        estimator_ = FxEstimator.get_estimator(estimator)
        if not estimator_:
            # raise ValueError(f"could not find estimator {estimator}")
            return None

        pair1 = FxPair.get_pair(pair=pair_1)
        pair2 = FxPair.get_pair(pair=pair_2)
        if not (pair1 or pair2):
            return None

        try:
            covar = FxSpotCovariance.objects.get(pair_1=pair1, pair_2=pair2,
                                                 data_cut=data_cut, estimator=estimator_).covariance
            return covar
        except Exception as e:
            pass

        # Try with the inverse, noting that Covar(LogRet(FX1), LogRet(FX2)) = Covar(LogRet(1/FX1), LogRet(1/FX2))
        pair1 = FxPair.get_inverse_pair(pair1)
        pair2 = FxPair.get_inverse_pair(pair2)
        covar = FxSpotCovariance.objects.get(pair_1=pair1, pair_2=pair2,
                                             data_cut=data_cut, estimator=estimator_).covariance
        return covar

    @staticmethod
    def get_covariance_objects(pair_1: FxPairTypes,
                               pair_2: FxPairTypes,
                               estimator: FxEstimatorTypes) -> Iterable['FxSpotCovariance']:
        return FxSpotCovariance.objects.filter(pair_1=pair_1, pair_2=pair_2, estimator=estimator)

    @staticmethod
    def get_covariance_matrix(pairs: Iterable[FxPair], estimator: FxEstimator, data_cut: DataCut):
        timing_start = Date.now()
        covars = FxSpotCovariance.objects.select_related().filter(pair_1__in=pairs, pair_2__in=pairs,
                                                                  estimator=estimator, data_cut=data_cut)
        timing_end = Date.now()
        logger.debug(f"  * get_covariance_matrix: {timing_end - timing_start} to get covars from DB.")

        timing_start = Date.now()
        indices = {}
        for it, pair in enumerate(pairs):
            indices[pair] = it

        pairs = np.array(pairs)
        matrix = np.zeros(shape=(len(pairs), len(pairs)))
        matrix[:, :] = np.nan
        for covar in covars:
            i1, i2 = indices[covar.pair_1], indices[covar.pair_2]
            matrix[i1, i2] = covar.covariance
        timing_end = Date.now()
        logger.debug(
            f"  * get_covariance_matrix: {timing_end - timing_start} to build matrix with "
            f"{len(pairs)} x {len(pairs)} entries.")

        return matrix

    @staticmethod
    def get_correlation_matrix(pairs: Iterable[FxPair], estimator: FxEstimator, data_cut: DataCut):
        # TODO: make it follow pattern of get_vols_at_time

        data_cut = FxSpotVol.objects.filter(estimator=estimator, data_cut__cut_time__lte=data_cut.cut_time) \
            .latest("data_cut__cut_time").data_cut

        corr = FxSpotCovariance.get_covariance_matrix(pairs=pairs, estimator=estimator, data_cut=data_cut)
        d = len(corr)

        vols = []
        for i in range(d):
            vols.append(np.sqrt(corr[i, i]))
        vols = np.array(vols)

        for i in range(d):
            corr[i, i] = 1.0
            for j in range(i + 1, d):
                product_vols = vols[i] * vols[j]
                if product_vols == 0:
                    logger.warning(f"Product of vols for pairs {i} and {j} is zero.")
                    corr[i, j] = 0
                    corr[j, i] = 0
                else:
                    rho = corr[i, j] / product_vols
                    corr[i, j] = rho
                    corr[j, i] = rho
        return corr

    @staticmethod
    @get_or_none
    def get_vols_as_series(data_cut: DataCut, estimator: FxEstimator, as_hdl_pairs: bool = False) -> pd.Series:
        vol_entries = FxSpotCovariance.objects.filter(data_cut=data_cut, estimator=estimator,
                                                      pair_1=models.F('pair_2'))

        pairs, vols = [], []
        for obj in vol_entries:
            pairs.append(obj.pair_1.to_FxPairHDL() if as_hdl_pairs else obj.pair_1)
            vols.append(np.sqrt(obj.covariance))
        return pd.Series(index=pairs, data=vols)

    @staticmethod
    @get_or_none
    def get_correlation(pair_1: FxPairTypes,
                        pair_2: FxPairTypes,
                        data_cut: DataCut,
                        estimator: FxEstimatorTypes = "Covar-Prod") -> Optional[float]:
        """
        Get the spot correlation between two fx pairs on a date
        :param pair_1: first FxPair
        :param pair_2: second FxPair
        :param data_cut: DataCut, the data cut for the correlation estimate
        :param estimator: the estimator id
        :return: float, the correlation between pairs for this data cut
        """
        pair_1 = FxPair.get_pair(pair_1)
        pair_2 = FxPair.get_pair(pair_2)

        if pair_1 == pair_2:
            return 1.0

        cov = FxSpotCovariance.get_covariance(pair_1=pair_1, pair_2=pair_2, data_cut=data_cut, estimator=estimator)
        vol1 = FxSpotCovariance._get_vol(fx_pair=pair_1, data_cut=data_cut, estimator=estimator)
        if not vol1:
            return None
        vol2 = FxSpotCovariance._get_vol(fx_pair=pair_2, data_cut=data_cut, estimator=estimator)
        if not vol2:
            return None

        rho = cov / (vol1 * vol2)
        rho = min(1.0, max(-1.0, rho))
        return rho

    ##################

    @staticmethod
    def get_variance_time_series(fxpair: FxPairTypes,
                                 estimator: Union[FxEstimatorId, FxEstimator]
                                 ) -> List[Tuple[datetime.datetime, float]]:
        return FxSpotCovariance.get_time_series(fxpair1=fxpair, fxpair2=fxpair, estimator=estimator)

    @staticmethod
    def get_volatility_time_series(fxpair: FxPairTypes,
                                   estimator: Union[FxEstimatorId, FxEstimator]
                                   ) -> List[Tuple[Date, float]]:
        ts = FxSpotCovariance.get_time_series(fxpair1=fxpair, fxpair2=fxpair, estimator=estimator)
        return [(d, np.sqrt(var)) for d, var in ts]

    @staticmethod
    def get_time_series(fxpair1: FxPairTypes,
                        fxpair2: FxPairTypes,
                        estimator: FxEstimatorTypes
                        ) -> List[Tuple[Date, float]]:
        data = FxSpotCovariance.objects.filter(pair_1=FxPair.get_pair(fxpair1),
                                               pair_2=FxPair.get_pair(fxpair2),
                                               estimator=FxEstimator.get_estimator(estimator))
        data = data.order_by("data_cut__cut_time")
        output = []
        for point in data:
            output.append((point.data_cut.cut_time, point.covariance))
        return output

    @staticmethod
    def get_correlation_time_series(fxpair1: FxPairTypes,
                                    fxpair2: FxPairTypes,
                                    estimator: FxEstimatorTypes
                                    ) -> List[Tuple[Date, float]]:
        fxpair1 = FxPair.get_pair(fxpair1)
        fxpair2 = FxPair.get_pair(fxpair2)

        # Get individual time series.
        covariance_data = FxSpotCovariance.get_time_series(fxpair1, fxpair2, estimator)
        variance1_data = FxSpotCovariance.get_time_series(fxpair1, fxpair1, estimator)
        variance2_data = FxSpotCovariance.get_time_series(fxpair2, fxpair2, estimator)

        output = []
        it1, it2, it3 = 0, 0, 0
        end1, end2, end3 = len(covariance_data), len(variance1_data), len(variance2_data)
        while it1 < end1 and it2 < end2 and it3 < end3:
            date_cv, cov = covariance_data[it1]
            date_v1, var1 = variance1_data[it2]
            date_v2, var2 = variance2_data[it3]

            next_date = max(date_cv, date_v1, date_v2)
            all_dates_equal = True
            if date_cv < next_date:
                all_dates_equal = False
                it1 += 1
            if date_v1 < next_date:
                all_dates_equal = False
                it2 += 1
            if date_v2 < next_date:
                all_dates_equal = False
                it3 += 1

            if all_dates_equal:
                v = var1 * var2
                if 0 < v:
                    rho = cov / np.sqrt(v)
                    rho = min(1.0, max(-1.0, rho))
                    output.append((next_date, rho))
                it1 += 1
                it2 += 1
                it3 += 1

        return output

    @staticmethod
    @get_or_none
    def _get_vol(fx_pair: FxPairTypes,
                 data_cut: DataCut,
                 estimator: FxEstimatorTypes) -> float:
        fx_pair = FxPair.get_pair(fx_pair)
        estimator = FxEstimator.get_estimator(estimator)
        try:
            var = FxSpotCovariance.objects.get(pair_1=fx_pair, pair_2=fx_pair,
                                               data_cut=data_cut, estimator=estimator).covariance
        except Exception as e:
            # Try to get vol for inverse pair
            fx_pair = fx_pair.get_inverse_pair(fx_pair)
            var = FxSpotCovariance.objects.get(pair_1=fx_pair, pair_2=fx_pair,
                                               data_cut=data_cut, estimator=estimator).covariance

        return np.sqrt(var)

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def add_spot_covariance(pair1: Union[FxPair, FxPairHDL],
                            pair2: Union[FxPair, FxPairHDL],
                            data_cut: DataCut,
                            estimator: FxEstimator,
                            covariance: float,
                            update: bool = False
                            ) -> Tuple[ActionStatus, 'FxSpotCovariance', 'FxSpotCovariance']:
        pair1 = FxPair.get_pair(pair1)
        pair2 = FxPair.get_pair(pair2)
        st1, cv1 = FxSpotCovariance._add_spot_covariance_not_inverse(pair1, pair2, data_cut,
                                                                     estimator, covariance, update)
        if pair1 != pair2:
            st2, cv2 = FxSpotCovariance._add_spot_covariance_not_inverse(pair2, pair1, data_cut,
                                                                         estimator, covariance,
                                                                         update)
            return ActionStatus.success(f"{st1}, {st2}"), cv1, cv2
        return ActionStatus.success(f"{st1}"), cv1, cv1

    @staticmethod
    def _add_spot_covariance_not_inverse(pair1: FxPair,
                                         pair2: FxPair,
                                         data_cut: DataCut,
                                         estimator: FxEstimator,
                                         covariance: float,
                                         update: bool = False) -> Tuple[ActionStatus, Optional['FxSpotCovariance']]:
        try:
            try:
                spot_covariance = FxSpotCovariance.objects.get(data_cut=data_cut,
                                                               pair_1=pair1,
                                                               pair_2=pair2,
                                                               estimator=estimator)
                if update:
                    spot_covariance.covariance = covariance
                    return ActionStatus.success(f"Updated spot covariance"), spot_covariance
                return ActionStatus.no_change("Did not update spot covariance"), spot_covariance
            except FxSpotCovariance.DoesNotExist:
                spot_covariance = FxSpotCovariance.objects.create(date=data_cut.date,
                                                                  data_cut=data_cut,
                                                                  pair_1=pair1,
                                                                  pair_2=pair2,
                                                                  estimator=estimator,
                                                                  covariance=covariance)
                return ActionStatus.success(
                    f"Added spot covariance for cut {data_cut.id} for pairs {pair1} ~ {pair2}, value = {covariance}"), \
                       spot_covariance
        except Exception as ex:
            return ActionStatus.error(f"Could not add spot covariance: {ex}"), None
