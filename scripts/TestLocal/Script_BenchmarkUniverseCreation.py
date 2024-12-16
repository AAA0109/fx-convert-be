import numpy as np
from matplotlib import pyplot as plt
from hdlib.DateTime.Date import Date
from hdlib.AppUtils.log_util import get_logger, logging
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.DEBUG)


def run():
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency

    USD = Currency.get_currency("USD")
    logger.debug("Starting universe creation")
    # Time how long universe construction takes
    start_time = Date.now()

    universe = UniverseProviderService().make_cntr_currency_universe(domestic=USD,
                                                                     ref_date=Date.create(ymd=2023_11_14),
                                                                     bypass_errors=True)
    end_time = Date.now()

    # Get the number of milliseconds between start_time and end_time
    milliseconds = (end_time - start_time)

    logger.debug(f"Finished universe creation, time was {milliseconds} seconds.")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
