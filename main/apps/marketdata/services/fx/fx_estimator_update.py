from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models.fx.rate import FxSpot
from main.apps.marketdata.models.fx.estimator import FxSpotCovariance
from main.apps.marketdata.models.fx.estimator import FxEstimator, FxEstimatorId, FxSpotVol
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.util import ActionStatus

from hdlib.DateTime.DayCounter import DayCounter_HD, DayCounter
from hdlib.DateTime.Date import Date

import numpy as np
from typing import List, Union, Sequence

# Universal default day counter
_dc = DayCounter_HD()


class FxEstimatorUpdateService(object):
    """
    Service responsible for performing updates to fx estimators (volatility, correlation, etc)
    """

    prod_estimator = FxEstimator.get_estimator_by_tag("Covar-Prod")

    @staticmethod
    def full_update(date: Date, estimator: FxEstimator = prod_estimator):
        """
        Update estimates of volatility and of covariance (and therefore of correlation).
        Uses the default production estimator by default.
        """
        FxEstimatorUpdateService.update_volatilities(date=date, estimator=estimator)
        FxEstimatorUpdateService.update_covariance(date=date, estimator=estimator)

    @staticmethod
    def update_volatilities(date: Date,
                            estimator: Union[FxEstimatorId, FxEstimator],
                            update: bool = False) -> ActionStatus:
        """
        Update all historical daily volatility estimates on a given date, using the volatilies known from the last date
        For example, this could be an
        :param date: Date, the date for which we need a new estimate
        :param estimator: int or FxEstimator, the estimator to use to perform the update
        :param update: bool, if true, overwrite any existing estimator.
        :return: ActionStatus, what happened
        """
        estimator = FxEstimator.get_estimator(estimator)
        if not estimator:
            return ActionStatus.error(f"Estimator {estimator} not found")

        # 1) Get all volatility estimates that use this estimator.
        annualization_factor = np.sqrt(_dc.year_fraction_from_days(1))

        # FxSpotVol -> date, pair, vol, estimator
        vols_for_estimator = FxSpotVol.objects.filter(estimator=estimator)
        fxpairs_for_update = vols_for_estimator.values("pair").distinct()

        # Keep track of any currency pairs for which there were errors.
        error_pairs: List[str] = []

        # Get the EOD cut for today.
        eod_cut = DataCutService.get_eod_cut(date=date)
        if eod_cut is None:
            raise RuntimeError(f"no EOD cut for {date}, cannot update volatility")

        for fx_pair in fxpairs_for_update:
            pair = FxPair.get_pair(fx_pair['pair'])
            # Get the last date on which there is an estimator for this pair.
            last_entry = vols_for_estimator.filter(date__lt=date).order_by('-date')[0]
            last_date = last_entry.date
            last_vol = last_entry.vol

            last_spot = FxSpot.objects.get(date=last_date, pair=pair).rate
            today_spot = FxSpot.objects.get(date=date, pair=pair).rate
            todays_return = np.log(today_spot / last_spot)

            var_topday = (todays_return / annualization_factor) ** 2
            last_var_estimate = last_vol ** 2

            try:
                var_estimate = estimator.estimate(value_topday=var_topday, estimator_lastday=last_var_estimate)
                vol_estimate = np.sqrt(var_estimate)
                # Save the vol to the 'database.'
                FxSpotVol.add_spot_vol(data_cut=eod_cut, fxpair=pair, vol=vol_estimate, estimator=estimator,
                                       update=update)
            except Exception as ex:
                error_pairs.append(f"{fx_pair}: {ex}")

        # If there were error updating volatility, return error status.
        if 0 < len(error_pairs):
            ActionStatus.error(f"Out of {len(fxpairs_for_update)} pairs, "
                               f"there were {len(error_pairs)} errors: {','.join(error_pairs)}")
        # Otherwise, return success.
        return ActionStatus.success("Successfully updated all spot volatilities")

    @staticmethod
    def update_covariance(date: Date,
                          estimator: Union[FxEstimatorId, FxEstimator],
                          update: bool = False) -> ActionStatus:
        estimator = FxEstimator.get_estimator(estimator)
        if not estimator:
            return ActionStatus.error(f"Estimator {estimator} not found")

        # 1) Get all volatility estimates that use this estimator.
        last_eod = DataCutService.get_last_eod_cut(date=date)
        eod_cut = DataCutService.get_eod_cut(date=date)

        if last_eod is None:
            return ActionStatus.error("No last EOD cut could be found.")

        # FxSpotVol -> date, pair, vol, estimator
        # TODO: Data cut.
        covariance_for_estimator = FxSpotCovariance.objects.filter(estimator=estimator, date__lt=date)
        # Get all distinct pairs that need estimating.
        pairs_for_estimator = covariance_for_estimator.values("pair_1", "pair_2").distinct()

        # Keep track of any pairs of currency pairs for which there were errors computing correlation.
        error_pairs: List[str] = []

        for fx_pairs in pairs_for_estimator:
            pair1 = FxPair.get_pair(fx_pairs['pair_1'])
            pair2 = FxPair.get_pair(fx_pairs['pair_2'])
            if pair2 < pair1:
                continue

            # Get the last date on which there is an estimator for this pair.
            last_entry = covariance_for_estimator.filter(pair_1=pair1, pair_2=pair2, date__lt=date).order_by(
                '-date').first()
            last_date = last_entry.date
            last_covariance = last_entry.covariance

            last_spot1 = FxSpot.objects.get(data_cut=last_eod, pair=pair1).rate
            today_spot1 = FxSpot.objects.get(data_cut=eod_cut, pair=pair1).rate

            last_spot2 = FxSpot.objects.get(data_cut=last_eod, pair=pair2).rate
            today_spot2 = FxSpot.objects.get(data_cut=eod_cut, pair=pair2).rate

            todays_return1 = np.log(today_spot1 / last_spot1)
            todays_return2 = np.log(today_spot2 / last_spot2)

            annualization_factor = _dc.year_fraction(start=Date.from_datetime_date(last_date),
                                                     end=Date.from_datetime_date(date))
            covariance_topday = todays_return1 * todays_return2 / annualization_factor

            try:
                var_estimate = estimator.estimate(value_topday=covariance_topday, estimator_lastday=last_covariance)
                # Save the vol to the 'database.'
                FxSpotCovariance.add_spot_covariance(pair1=pair1,
                                                     pair2=pair2,
                                                     data_cut=eod_cut,
                                                     estimator=estimator,
                                                     covariance=var_estimate,
                                                     update=update)
            except Exception as ex:
                error_pairs.append(f"{pair1} ~ {pair2}: {ex}")

        # If there were error updating volatility, return error status.
        if 0 < len(error_pairs):
            ActionStatus.error(f"Out of {len(pairs_for_estimator)} pairs or fxpairs, "
                               f"there were {len(error_pairs)} errors: {','.join(error_pairs)}")
        # Otherwise, return success.
        return ActionStatus.success("Successfully updated all spot covariances")

    @staticmethod
    def update_covariance_for_fxpairs(date: Date,
                                      estimator: Union[FxEstimatorId, FxEstimator],
                                      fxpair1: FxPair,
                                      fxpair2: FxPair) -> ActionStatus:

        estimator_ = FxEstimator.get_estimator(estimator)
        if not estimator_:
            return ActionStatus.error(f"Estimator {estimator_} not found")

        # TODO: Get last cut that has EOD for both pairs.

        last_eod = DataCutService.get_last_eod_cut(date=date)
        eod_cut = DataCutService.get_eod_cut(date=date)

        fx_provider = FxSpotProvider()  # TODO: inject into constructor of this service
        last_spot_cache = fx_provider.get_eod_spot_fx_cache(date=last_eod.date)
        today_spot_cache = fx_provider.get_eod_spot_fx_cache(date=date)

        if last_eod is None:
            return ActionStatus.error("No last EOD cut could be found.")
        if eod_cut is None:
            return ActionStatus.log_and_error(f"No EOD cut for this date ({date})")

        last_date = last_eod.date

        if date == last_date:
            raise ValueError(f"Date = Last date, date is {date}. Last EOD cut {last_eod}, this EOD {eod_cut}.")

        last_covariance = FxSpotCovariance.get_covariance(pair_1=fxpair1, pair_2=fxpair2,
                                                          data_cut=last_eod, estimator=estimator_)

        last_spot1 = last_spot_cache.get_fx(fx_pair=fxpair1)
        today_spot1 = today_spot_cache.get_fx(fx_pair=fxpair1)

        last_spot2 = last_spot_cache.get_fx(fx_pair=fxpair2)
        today_spot2 = today_spot_cache.get_fx(fx_pair=fxpair2)

        if today_spot1 is None or today_spot2 is None or last_spot1 is None or last_spot2 is None:
            FxSpotCovariance.add_spot_covariance(pair1=fxpair1,
                                                 pair2=fxpair2,
                                                 data_cut=eod_cut,
                                                 estimator=estimator,
                                                 covariance=last_covariance,
                                                 update=True)
            return ActionStatus.log_and_no_change(f"Some spots were None, so last covariance is being carried over.")

        todays_return1 = np.log(today_spot1 / last_spot1)
        todays_return2 = np.log(today_spot2 / last_spot2)

        annualization_factor = _dc.year_fraction(start=last_date, end=date)
        covariance_topday = todays_return1 * todays_return2 / annualization_factor

        try:
            var_estimate = estimator.estimate(value_topday=covariance_topday, estimator_lastday=last_covariance)
            # Save the vol to the 'database.'
            FxSpotCovariance.add_spot_covariance(pair1=fxpair1,
                                                 pair2=fxpair2,
                                                 data_cut=eod_cut,
                                                 estimator=estimator,
                                                 covariance=var_estimate,
                                                 update=True)
            return ActionStatus.success(f"Successfully updated covariance for {fxpair1} ~ {fxpair2}"
                                        f" to be {var_estimate}")
        except Exception as ex:
            pass
