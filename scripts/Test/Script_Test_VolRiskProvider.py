import os
import sys

import numpy as np
from hdlib.DateTime.DayCounter import DayCounter_HD
from matplotlib import pyplot as plt

from hdlib.DateTime.Date import Date
from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.risk_metric.services.cashflow_risk_provider import CashFlowRiskService
    from main.apps.currency.models import FxPair
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

    vol_averaging_days = 90
    history_plot_days = 365
    future_plot_days = 90
    plot_future_spots = True

    eurusd = FxPair.get_pair("EUR/USD")
    last_date = Date.from_int(20220101)
    vol = CashFlowRiskService().get_fxpair_realized_volatility(fxpair=eurusd,
                                                               last_date=last_date,
                                                               averaging_window=vol_averaging_days)
    fx_ts = FxSpotProvider().get_eod_spot_time_series(start_date=last_date - history_plot_days,
                                                      end_date=last_date,
                                                      fx_pair=eurusd)
    if 0 < len(fx_ts):
        t, spot = zip(*fx_ts)

        plt.figure(figsize=[12, 8])
        plt.plot(t, spot, label=f"Fx Spot time series for {eurusd}", marker="x", color="blue")

        dc = DayCounter_HD()
        final_spot, final_date = spot[-1], Date.from_datetime(t[-1])
        dates, lower_bounds, upper_bounds = [], [], []
        for i in range(0, future_plot_days):
            log_return = vol * np.sqrt(dc.year_fraction_from_days(i))
            # Upper log(upper / final_spot) = log_return
            upper = final_spot * np.exp(log_return)
            # Upper log(lower / final_spot) = -log_return
            lower = final_spot * np.exp(-log_return)

            dates.append(final_date + i)
            lower_bounds.append(lower)
            upper_bounds.append(upper)

        plt.fill_between(dates, lower_bounds, upper_bounds, color="mistyrose")
        plt.plot(dates, lower_bounds, color="red", label=f"Vol cone, vol = {vol:.4f}")
        plt.plot(dates, upper_bounds, color="red")

        # Plot what no change would have been.
        plt.plot([final_date, dates[-1]], [final_spot, final_spot], color="black", linestyle="--")

        if plot_future_spots:
            fx_ts = FxSpotProvider().get_eod_spot_time_series(start_date=final_date,
                                                              end_date=final_date + future_plot_days,
                                                              fx_pair=eurusd)
            t, spot = zip(*fx_ts)
            plt.plot(t, spot, color="darkgray", label=f"Realized Fx Spot for {eurusd}", marker="+")

        plt.xlabel("Date")
        plt.ylabel("Fx Spot")
        plt.legend()
        plt.title(f"Volatility risk for {eurusd}")
        plt.show()


if __name__ == '__main__':
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
