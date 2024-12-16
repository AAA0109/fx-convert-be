import logging

from django.core.management.base import BaseCommand

from main.apps.marketdata.services.estimators.covariance import CovarianceEstimatorCreator


class Command(BaseCommand):
    help = 'Run covariance estimator seed script'

    def add_arguments(self, parser):
        parser.add_argument('--pair1_id', type=int)
        parser.add_argument('--pair2_id', type=int, default=None)
        parser.add_argument('--parameters', nargs='?', type=float, default=0.99)
        parser.add_argument('--min_date', nargs='?', type=str, default=None)

    def handle(self, *args, **options):
        try:
            tag = "Covar-Prod"
            pair1 = options['pair1_id']
            pair2 = options['pair2_id']
            parameters = options['parameters']
            min_date = options['min_date']

            logging.info(
                f"Running covariance estimator (tag={tag}) for "
                f"pair1={pair1} and pair2={pair2 or 'all pairs'}.")

            covariance_estimator_creator = CovarianceEstimatorCreator(
                pair1=pair1,
                pair2=pair2,
                tag=tag,
                parameters=parameters,
                min_date=min_date
            )
            covariance_estimator_creator.execute()
            logging.info("Command executed successfully!")
        except Exception as e:
            logging.error(e)
            raise Exception(e)
