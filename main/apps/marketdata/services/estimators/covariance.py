import logging
from abc import ABC
from datetime import datetime
import time

import numpy as np
from django.core.cache import cache
from django_bulk_load import bulk_upsert_models
from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD

from main.apps.currency.models import FxPair
from main.apps.marketdata.models import FxEstimator, FxSpotCovariance
from main.apps.marketdata.models.fx.rate import FxSpot
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from django.db.models import Prefetch


logger = logging.getLogger(__name__)

class CovarianceEstimatorCreator(ABC):
    pair1: FxPair = None
    pair2: FxPair = None
    covariance_sample = 100
    min_date = None

    def __init__(self, pair1, pair2, tag: str, parameters: float = None, min_date: str = None):
        self.pair1 = FxPair.get_pair(pair1)
        if pair2 is not None:
            self.pair2 = FxPair.get_pair(pair2)
        self.tag = tag
        self.parameters = parameters
        self.dc = DayCounter_HD()
        if min_date is not None:
            self.min_date = Date.from_str(min_date)

    def execute(self):
        logger.info(f"Starting covar calculation method for {self.pair1} and {self.pair2 or 'all pairs'}")
        start_time = time.time()
        estimator = FxEstimator.get_estimator_by_tag(self.tag)
        fx_spot_provider = FxSpotProvider()
        
        fxpair1 = self.pair1

        # try to get the rate time series from cache
        max_date = datetime.now().strftime("%Y-%m-%d")
        cache_key_fxpair1 = f'fxspot_pair_{fxpair1.pk}_rate_ts_on_{max_date}'
        cache_fxpair1 = cache.get(cache_key_fxpair1)
        all_pairs = [self.pair2] if self.pair2 is not None else FxPair.get_pairs()

        fxspots1_start_time = time.time()
        fxspots1 = cache_fxpair1 if cache_fxpair1 is not None \
            else fx_spot_provider.get_rate_time_series(fx_pair=fxpair1, min_date=self.min_date)
        fxspots1_time_taken = time.time() - fxspots1_start_time
        
        for fxpair2 in all_pairs:
            pair_start_time = time.time()
            logger.info(f"Starting calculation for pairs {fxpair1} ~ {fxpair2}, estimator tag = {self.tag}")

            # try to get the rate time series from cache
            cache_key_fxpair2 = f'fxspot_pair_{fxpair2.pk}_rate_ts_on_{max_date}'
            cache_fxpair2 = cache.get(cache_key_fxpair2)

            fxspots2 = cache_fxpair2 if cache_fxpair2 is not None \
                else fx_spot_provider.get_rate_time_series(fx_pair=fxpair2, min_date=self.min_date)

            if len(fxspots1) == 0 or len(fxspots2) == 0:
                logger.warning(f"No data for {fxpair1} or {fxpair2}. No covar to estimate.")
                continue

            start_date = np.maximum(fxspots1[0][0], fxspots2[0][0])
            end_date = np.minimum(fxspots1[-1][0], fxspots2[-1][0])

            # Enlarge the range of dates to the beginning / end of days to make sure there
            eod_data_cuts = np.array(DataCutService.get_eod_cuts_in_range(start_date.start_of_day(),
                                                                          end_date.start_of_next_day()))

            it1, it2, itd = 0, 0, 0
            date1, spot1 = fxspots1[it1]
            date2, spot2 = fxspots2[it1]

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
                        logging.error(
                            f"Had to stop calculating covar for {fxpair1} ~ {fxpair2} because there are no more "
                            f"data cuts, even though there was data. Date = {date}.")
                        break  # Ran out of EOD cuts.
                    data_cut = eod_data_cuts[itd]

                    annualization_factor = self.dc.year_fraction(start=last_date, end=date)
                    covar = np.log(spot1 / last_spot1) * np.log(spot2 / last_spot2) / annualization_factor

                    last_var_estimate = covar if last_var_estimate is None else last_var_estimate

                    var_estimate = estimator.estimate(value_topday=covar, estimator_lastday=last_var_estimate)

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

            logger.info(f"Creating {len(data)} covar entries")

            BATCH_SIZE = 1000
            for i in range(0, len(data), BATCH_SIZE):
                batch = data[i:i+BATCH_SIZE]
                FxSpotCovariance.objects.bulk_create(batch, ignore_conflicts=True)
            logger.info(f"Completed covar calculation for {fxpair1} {fxpair2}. Time taken: {time.time() - pair_start_time:.2f} seconds")