import sys
import os
import time

from hdlib.Core.Currency import USD, ILS

from hdlib.Compute.MarginCalculation import IBMarginCalculator
from hdlib.DateTime.Date import Date

from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


def run():
    from main.apps.hedge.services.broker import BrokerService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.marketdata.services.data_cut_service import DataCutService
    from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi

    # Get caches and create a calculator.
    # margin_rates_cache = MarginProviderService().create_margin_rates_cache("IBKR")
    data_cut = DataCutService.get_latest_cut()
    spot_fx_cache = FxSpotProvider().get_spot_cache(time=Date.from_datetime(data_cut.cut_time))
    # calculator = IBMarginCalculator(margin_rates_cache=margin_rates_cache, spot_fx_cache=spot_fx_cache)

    summary = BrokerService().get_allsummary_broker_account_data()

    all_summaries = BrokerService().get_all_broker_account_data()
    positions_by_account = {}

    for broker_account, summary in all_summaries.items():
        positions_by_account[broker_account] = BrokerService().get_broker_account_positions(
            broker_account=broker_account)

    for broker_account, summary in all_summaries.items():
        positions = positions_by_account[broker_account]
        print(broker_account)
        fmm = summary.full_maint_margin_req
        print(f" * Maintenance margin requirement: {fmm}")
        print(f" * Initial margin requirement: {summary.full_init_margin_req}")
        print(f" * Accrued cash: {summary.accrued_cash}")
        print(f" * Available funds: {summary.available_funds}")
        print(f" * Positions:")

        for position in positions:
            print(f"   -> {position.fxpair}: {position.amount} (avg cost: {position.average_price})")

        # margin_estimate = calculator.compute_margin_from_vfx(virtual_fx=positions,
        #                                                      domestic=USD,
        #                                                      additional_cash={USD: summary.available_funds})

        # print(f"Estimated margin: {margin_estimate} ({100 * margin_estimate / fmm if 0 < fmm else 100.0}% of actual)")

        print()
    pass


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
