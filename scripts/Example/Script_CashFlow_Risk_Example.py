import os, sys

from scripts.lib.only_local import only_allow_local

"""
Example Script for running cashflow risk. To run, you must first have:
1) Loaded all account related fixtures
2) Run the Script_Add_MarketData_Example
"""


def run():
    from main.apps.risk_metric.services.cashflow_risk_provider import CashFlowRiskService
    from main.apps.account.services.cashflow_provider import CashFlowProviderService
    from main.apps.account.services.cashflow_pricer import CashFlowPricerService
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.account.models.account import Account
    from main.apps.currency.models.fxpair import FxPair
    from main.apps.account.models.company import Company
    from main.apps.account.models.cashflow import CashFlow
    from hdlib.DateTime.Date import Date
    import matplotlib.pyplot as plt

    from hdlib.AppUtils.log_util import get_logger, logging
    logger = get_logger(level=logging.INFO)

    ref_date = Date.from_int(20211028)  # just for example, in general dont pass a date for live hedge
    domestic_str = 'EUR'

    # =======================
    # Add a new company
    # =======================
    company = Company.create_company(name=f"CF Risk Company {domestic_str}", currency=domestic_str)
    domestic = company.currency
    CashFlow.objects.filter(account__company=company).delete()

    # =======================
    # Add An Account for that company
    # =======================
    account = Account.get_account(name=(company.name, "Main Account"))
    if not account:
        account = Account.create_account(name="Main Account", company=company)

    # =======================
    # Add some permissible currencies for that account
    # =======================
    if account is None:
        logger.error("Account was None. This is likely because the account failed to be created. Cannot continue.")
        return

    # =======================
    # Add some cashflows to the account
    # =======================
    test_currencies = ["GBP", "AUD"]
    # if domestic_str != 'USD':
    #     test_currencies.append("USD")
    for date in [20211101, 20211201, 20220201, 20220301, 20220401, 20220501]:
        for currency in test_currencies:
            CashFlow.create_cashflow(account=account,
                                     date=Date.from_int(date),
                                     currency=currency,
                                     amount=1024.25,
                                     status=CashFlow.CashflowStatus.ACTIVE)
    get_historical_cash = False
    get_npv = False
    get_simulated_risk = False
    get_risk_cones = True
    test_universe = False

    if test_universe:
        # ref_date = Date(2022, 8, 15)
        fx_pairs = FxPair.get_foreign_to_domestic_pairs(domestic=domestic, foreign_names=["GBP", "AUD"])

        # Construct the Financial Universe
        universe = UniverseProviderService().make_cntr_currency_universe(ref_date=ref_date,
                                                                         domestic=domestic,
                                                                         fx_pairs=fx_pairs)
    cashflow_pricer = CashFlowPricerService()

    if get_historical_cash:
        historical_cash, num_flows = cashflow_pricer.get_historical_cashflows_value_for_account(
            start_date=ref_date - 20,
            end_date=ref_date,
            account=account)
        print(historical_cash)

    if get_npv:
        npv, abs_npv = cashflow_pricer.get_npv_for_account(date=ref_date, account=account)
        print(npv, abs_npv)

    if get_simulated_risk:
        risk, pnl = CashFlowRiskService().get_simulated_risk_for_account(date=ref_date, account=account)
        print(risk)
        plt.hist(pnl)
        plt.xlabel('pnl')
        plt.show()

    if get_risk_cones:
        import matplotlib.pyplot as plt
        import numpy as np
        flows = CashFlowProviderService().get_active_hdl_cashflows_by_currency(ref_date=ref_date,
                                                                               account=account)

        do_std_devs = False
        reductions = [0.0, 0.33, 0.66, 0.8]
        std_devs = (1, 2, 3, 4)
        out = CashFlowRiskService().get_cashflow_risk_cones(domestic=domestic, cashflows=flows, start_date=ref_date,
                                                            end_date=ref_date + 50,
                                                            risk_reductions=reductions,
                                                            std_dev_levels=std_devs,
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
            for i in range(len(reductions)):
                upper_max = np.round(out['upper_max_percents'][i], 2)
                lower_max = np.round(out['lower_max_percents'][i], 2)
                plt.plot(out['uppers'][i],
                         label=f'{np.round(reductions[i] * 100, 2)}%, {upper_max, lower_max}% of value',
                         color=colors[i])
                plt.plot(out['lowers'][i], color=colors[i])

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
