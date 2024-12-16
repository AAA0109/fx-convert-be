import logging
from datetime import datetime

from django.core.cache import cache
from django.core.management.base import BaseCommand

from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider


class Command(BaseCommand):
    help = 'Cache FxSpot rate time series'

    def add_arguments(self, parser):
        parser.add_argument('--pair_id', type=int)
        parser.add_argument('--min_date', nargs='?', type=str, default=None)
        parser.add_argument('--timout', type=int, default=None)
        parser.add_argument('--delete', type=bool, default=True)

    def handle(self, *args, **options):
        try:
            pair_id = options['pair_id']
            min_date = options['min_date']
            timout = options['timout']
            delete = options['delete']
            max_date = datetime.now().strftime("%Y-%m-%d")
            cache_key = f'fxspot_pair_{pair_id}_rate_ts_on_{max_date}'

            logging.info(f"Deleting FxSpot (pair={pair_id}) cache for (key={cache_key}).")

            if delete:
                cache.delete(cache_key)

            logging.info(f"Caching FxSpot rate time series for pair={pair_id}.")
            rate_time_series = FxSpotProvider().get_rate_time_series(fx_pair=pair_id, min_date=min_date)
            cache.set(cache_key, rate_time_series, timout)
            logging.info("Command executed successfully!")
        except Exception as e:
            logging.error(e)
            raise Exception(e)
