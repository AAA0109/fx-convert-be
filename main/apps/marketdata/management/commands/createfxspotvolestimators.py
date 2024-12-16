import logging

from django.core.management.base import BaseCommand

from main.apps.marketdata.services.estimators.fxspotvol import FxSpotVolEstimatorCreator


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            tag = "Covar-Prod"
            logging.info(f"Running FxSpot volatility estimator (tag={tag}).")
            fx_spot_vol_estimator_creator = FxSpotVolEstimatorCreator(tag=tag)
            fx_spot_vol_estimator_creator.execute()
            logging.info("Command executed successfully!")
        except Exception as e:
            logging.error(e)
            raise Exception(e)
