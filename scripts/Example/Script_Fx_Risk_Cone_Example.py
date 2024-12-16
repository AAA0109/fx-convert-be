import os, sys

from scripts.lib.only_local import only_allow_local

"""
Example Script for running cashflow risk. To run, you must first have:
1) Loaded all account related fixtures
2) Run the Script_Add_MarketData_Example
"""


def run():
    from main.apps.risk_metric.services.cashflow_risk_provider import FxRiskService
    from main.apps.currency.models.fxpair import FxPair
    from hdlib.DateTime.Date import Date
    import matplotlib.pyplot as plt
    import numpy as np

    from hdlib.AppUtils.log_util import get_logger, logging
    logger = get_logger(level=logging.INFO)

    ref_date = Date.from_int(20211028)  # just for example, in general dont pass a date for live hedge

    # foreign_str = 'GBP'
    # domestic_str = 'USD'
    foreign_str = 'USD'
    domestic_str = 'GBP'

    fx_pair = FxPair.get_foreign_to_domestic_pairs(domestic=domestic_str, foreign_names=[foreign_str, ])[0]

    probs = (0.7, 0.95, 0.99)
    do_std_devs = True
    std_devs = (1, 2, 3)
    out = FxRiskService().get_single_fx_risk_cones(start_date=ref_date,
                                                   end_date=ref_date + 50,
                                                   prob_levels=probs,
                                                   std_dev_levels=std_devs,
                                                   fx_pair=fx_pair,
                                                   do_std_dev_cones=do_std_devs)
    plt.plot(out['means'], color='k')
    colors = ['r', 'y', 'g', 'b']

    initial_value = np.round(out["initial_value"], 2)
    plt.title(f"Risk Cones, Initial Value: {initial_value} {domestic_str}")

    if do_std_devs:
        for i in range(len(std_devs)):
            upper_max = np.round(out['upper_max_percents'][i], 2)
            lower_max = np.round(out['lower_max_percents'][i], 2)
            prob = np.round(100 * out['std_probs'][i], 3)
            plt.plot(out['uppers'][i],
                     label=f'{std_devs[i]} std dev, {upper_max, lower_max}% of value, ({prob}% prob)',
                     color=colors[i])
            plt.plot(out['lowers'][i], color=colors[i])
    else:
        raise NotImplementedError("TODO")
        # for i in range(len(reductions)):
        #     upper_max = np.round(out['upper_max_percents'][i], 2)
        #     lower_max = np.round(out['lower_max_percents'][i], 2)
        #     plt.plot(out['uppers'][i],
        #              label=f'{np.round(reductions[i] * 100, 2)}%, {upper_max, lower_max}% of value',
        #              color=colors[i])
        #     plt.plot(out['lowers'][i], color=colors[i])

    plt.ylabel(f'Risk ({domestic_str})')
    plt.xlabel('Date')
    plt.legend()
    plt.show()


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
