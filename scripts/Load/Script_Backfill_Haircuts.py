"""
Script to backfill a history of Margin Haircuts based on simple VaR model
"""

import os
import sys

from hdlib.DateTime.Date import Date

import numpy as np
from scipy.stats import norm
from scipy.stats import t

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def backfill_pair_for_date(broker, fx_pair, vol, data_cut, var_level: float = 0.999):
    from main.apps.margin.models.margin import FxSpotMargin
    daily_var = vol * vol / 252
    daily_vol = np.sqrt(daily_var)
    hp = 2
    vol_hp = np.sqrt(hp * daily_var)

    # 2) Compute the haircut from the vol
    var_rate = norm.ppf(var_level, loc=0, scale=vol_hp)  # per holding

    nu = 3
    scalar = np.sqrt(nu / (nu - 2))
    var_rate_t = t.ppf(var_level, 3) * vol_hp / scalar

    avg = (var_rate + var_rate_t) / 2

    # 3) Add the haircut to model
    FxSpotMargin.set_rate(fx_pair=fx_pair, margin_rate=avg, data_cut=data_cut, broker=broker, update=True)


def backfill_pair_for_dates(broker, fx_pair, eod_cut_map):
    from main.apps.marketdata.services.fx.fx_provider import FxVolAndCorrelationProvider

    logger.debug(f"Loading Vols Series for {fx_pair}")
    all_vols = FxVolAndCorrelationProvider().get_time_series(fxpair=fx_pair)
    logger.debug(f"Found {len(all_vols)} dates on which we can compute margin rate for {fx_pair}")

    for date, vol in all_vols:
        date = Date.to_date(date)
        try:
            # eod_cut = DataCutService.get_eod_cut(date=date, cuts=all_cuts)
            eod_cut = eod_cut_map.get(date.date(), None)
            if not eod_cut:
                raise ValueError("Couldnt find the cut in map, this shouldn't have occured")
            backfill_pair_for_date(broker, fx_pair, vol, data_cut=eod_cut)
        except Exception as e:
            logger.error(f"Error filling pair {fx_pair} on {date}: {e}")


def backfill_haircuts(broker_name: str = "IBKR"):
    from main.apps.marketdata.services.data_cut_service import DataCutService
    from main.apps.broker.models.broker import Broker
    from main.apps.currency.models.fxpair import FxPair

    broker = Broker.get_broker(broker_name)

    # Get all pairs linked to USD
    pairs = FxPair.get_foreign_to_domestic_pairs(domestic="USD")

    # Read in all the cuts first, makes the computation much faster
    all_cuts = DataCutService.get_all_eod_cuts()

    eod_cut_map = {cut.date.date(): cut for cut in all_cuts}

    for pair in pairs:
        logger.debug(f"Backfilling margin rates for pair: {pair}")
        backfill_pair_for_dates(broker=broker, fx_pair=pair, eod_cut_map=eod_cut_map)


def run():
    backfill_haircuts()


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
