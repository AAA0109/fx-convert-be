"""
Create volatility and correlation estimators so that they can be loaded into the universe.

"""

import os
import sys
from typing import Tuple, Iterable

import numpy as np
from matplotlib import pyplot as plt

from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.AppUtils.log_util import get_logger, logging
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def plot_ts(time_series: Iterable[Tuple[Date, float]], label: str = None):
    d, v = zip(*time_series)
    if label is not None:
        plt.plot(d, v, label=label)
    else:
        plt.plot(d, v)


def create_estimators_for_pairs(fxpair1, fxpair2, tag: str):
    from main.apps.marketdata.models import FxEstimator, FxSpotCovariance
    from main.apps.marketdata.services.data_cut_service import DataCutService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

    fx_spot_provider = FxSpotProvider()

    _dc = DayCounter_HD()

    logger.debug(f"Starting calculation for pairs {fxpair1} ~ {fxpair2}, estimator tag = {tag}")

    estimator = FxEstimator.get_estimator_by_tag(tag)

    logger.debug(f"Fetching data...")
    fxspots1 = fx_spot_provider.get_rate_time_series(fxpair1)
    fxspots2 = fx_spot_provider.get_rate_time_series(fxpair2)

    if len(fxspots1) == 0:
        logger.debug(f"No data for {fxpair1}. No covar to estimate.")
        return
    if len(fxspots2) == 0:
        logger.debug(f"No data for {fxpair2}. No covar to estimate.")
        return

    start_date = np.maximum(fxspots1[0][0], fxspots2[0][0])
    end_date = np.minimum(fxspots1[-1][0], fxspots2[-1][0])

    logger.debug(f"For pairs {fxpair1}, {fxpair2}, found {len(fxspots1)} and {len(fxspots2)} spots. Common date range "
                f"extends from {start_date} until {end_date}, {_dc.days_between(start_date, end_date)} days.")

    # Enlarge the range of dates to the beginning / end of days to make sure there
    eod_data_cuts = np.array(DataCutService.get_eod_cuts_in_range(start_date.start_of_day(),
                                                                  end_date.start_of_next_day()))

    it1, it2, itd = 0, 0, 0
    date1, spot1 = fxspots1[it1]
    date2, spot2 = fxspots2[it1]

    logger.debug(f"Starting calculation.")

    last_date, last_spot1, last_spot2, last_var_estimate = None, None, None, None
    data = []
    count = 0
    while True:
        count += 1

        if date1 < date2:
            it1 += 1
            if len(fxspots1) <= it1:
                break
            date1, spot1 = fxspots1[it1]
            continue
        if date2 < date1:
            it2 += 1
            if len(fxspots2) <= it2:
                break
            date2, spot2 = fxspots2[it2]
            continue

        # Here, date1 == date2
        date = date1
        if last_date:
            # Find the data cut.
            while itd < len(eod_data_cuts) and eod_data_cuts[itd].cut_time.date() < date.date():
                itd += 1
            if len(eod_data_cuts) <= itd:
                # This shouldn't be able to happen since the data is EOD data.
                logger.error(f"Had to stop calculating covar for {fxpair1} ~ {fxpair2} because there are no more "
                             f"data cuts, even though there was data. Date = {date}.")
                break  # Ran out of EOD cuts.
            data_cut = eod_data_cuts[itd]

            annualization_factor = _dc.year_fraction(start=last_date, end=date)
            covar = np.log(spot1 / last_spot1) * np.log(spot2 / last_spot2) / annualization_factor

            last_var_estimate = covar if last_var_estimate is None else last_var_estimate

            var_estimate = estimator.estimate(value_topday=covar, estimator_lastday=last_var_estimate)
            # data_cut = DataCutService.get_eod_cut(date=date)

            spot_covar = FxSpotCovariance(
                date=date,
                data_cut=data_cut,
                pair_1=fxpair1,
                pair_2=fxpair2,
                estimator=estimator,
                covariance=var_estimate)
            data.append(spot_covar)

            last_var_estimate = var_estimate

        last_date = date
        last_spot1, last_spot2 = spot1, spot2
        it1 += 1
        it2 += 1
        if len(fxspots1) <= it1 or len(fxspots2) <= it2:
            break
        date1, spot1 = fxspots1[it1]
        date2, spot2 = fxspots2[it2]

    logger.debug(f"Finished calculation. Creating {len(data)} covar entries.")
    FxSpotCovariance.objects.bulk_create(data)
    logger.debug(f"Done uploading data to DB.")


def create_covariance_estimators(tag: str, parameters: float, only_usd_related: bool = True):
    from main.apps.marketdata.models import FxEstimator
    from main.apps.currency.models import FxPair, Currency

    status, estimator = FxEstimator.create_estimator(type=FxEstimator.EstimatorType.EWMA,
                                                     tag=tag, parameters=parameters)
    logger.debug(status)

    all_pairs = [fx for fx in FxPair.objects.all()]

    USD = Currency.get_currency("USD")

    # Calculate all covariances.
    for i in range(len(all_pairs) - 1):
        fxpair1 = all_pairs[i]

        if only_usd_related and fxpair1.base_currency != USD and fxpair1.quote_currency != USD:
            continue

        for j in range(i, len(all_pairs)):
            fxpair2 = all_pairs[j]

            if only_usd_related and fxpair2.base_currency != USD and fxpair2.quote_currency != USD:
                continue

            create_estimators_for_pairs(fxpair1=fxpair1, fxpair2=fxpair2, tag=tag)


def create_fx_spot_vol_estimators(tag: str):
    from main.apps.currency.models import FxPair
    from main.apps.marketdata.models import FxSpotVol, FxSpotCovariance, FxEstimator

    estimator = FxEstimator.get_estimator(tag)

    all_pairs = FxPair.get_all_pairs()
    for fxpair in all_pairs:
        all_variances = FxSpotCovariance.get_covariance_objects(pair_1=fxpair, pair_2=fxpair, estimator=estimator)
        data = []
        for variance in all_variances:
            vol = np.sqrt(variance.covariance)
            data_cut = variance.data_cut
            fx_spot_vol = FxSpotVol(date=data_cut.date, data_cut=data_cut, pair=fxpair, estimator=estimator, vol=vol)
            data.append(fx_spot_vol)

        FxSpotVol.objects.bulk_create(data)

        logger.debug(f"Finished calculating volatility for {fxpair}.")


def plot_correlations(tag: str, only_usd_related: bool = True):
    from main.apps.currency.models import FxPair, Currency
    from main.apps.marketdata.models import FxSpotCovariance, FxEstimator

    estimator = FxEstimator.get_estimator(estimator=tag)
    USD = Currency.get_currency("USD")

    # Start the plot.
    plt.figure(figsize=[10, 8])

    all_pairs = [fx for fx in FxPair.objects.all()]

    count = 0
    for it1, fxpair1 in enumerate(all_pairs):
        if only_usd_related and fxpair1.base_currency != USD and fxpair1.quote_currency != USD:
            continue

        for it2, fxpair2 in enumerate(all_pairs):
            if it2 <= it1:
                continue

            if only_usd_related and fxpair2.base_currency != USD and fxpair2.quote_currency != USD:
                continue

            correlation = FxSpotCovariance.get_correlation_time_series(fxpair1=fxpair1,
                                                                       fxpair2=fxpair2,
                                                                       estimator=estimator)
            if 0 < len(correlation):
                plot_ts(correlation, label=f"Correlation {fxpair1} ~ {fxpair2}")
                logger.debug(f"Plotted correlation for {fxpair1} ~ {fxpair2}.")

                if count == 10:
                    break
        if count == 10:
            break

    # End plot.
    plt.title("Correlation")
    plt.legend()
    plt.show()
    plt.close()


def run():
    tag = "Covar-Prod"
    do_plot = False

    plot_correlations(tag)
    return

    create_covariance_estimators(tag=tag, parameters=0.99)
    create_fx_spot_vol_estimators(tag=tag)
    if do_plot:
        plot_correlations(tag=tag)


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
