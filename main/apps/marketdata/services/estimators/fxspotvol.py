from abc import ABC
import logging
from django.db import transaction
import numpy as np

from django_bulk_load import bulk_upsert_models

from main.apps.currency.models import FxPair
from main.apps.marketdata.models import FxSpotVol
from main.apps.marketdata.models import FxSpotCovariance, FxEstimator

logger = logging.getLogger(__name__)

class FxSpotVolEstimatorCreator(ABC):
    tag: str

    def __init__(self, tag, pair_id):
        self.tag = tag
        self.pair_id = pair_id
    
    def execute(self):
        estimator = FxEstimator.get_estimator(self.tag)
        fxpair = FxPair.objects.get(id=self.pair_id)

        logger.info(f"Calculating volatility for {self.tag} - {fxpair}")
        all_variances = FxSpotCovariance.get_covariance_objects(pair_1=fxpair, pair_2=fxpair, estimator=estimator)
        data = []
        for variance in all_variances:
            vol = np.sqrt(variance.covariance)
            data_cut = variance.data_cut
            fx_spot_vol = FxSpotVol(date=data_cut.date, data_cut=data_cut, pair=fxpair, estimator=estimator, vol=vol)
            data.append(fx_spot_vol)

        logger.info(f"Upserting {len(data)} FxSpotVol objects for {fxpair}")
        with transaction.atomic():
            bulk_upsert_models(
                models=data,
                pk_field_names=['data_cut_id', 'estimator_id', 'pair_id']
            )
            logger.info(f"Finished calculating volatility for {fxpair}.")
            return f"Completed volatility calculation for {fxpair}"