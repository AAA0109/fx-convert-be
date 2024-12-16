import numpy as np
from matplotlib import pyplot as plt

from hdlib.Core.Currency import USD

from hdlib.DateTime.Date import Date
from hdlib.Instrument.RecurringCashFlowGenerator import RecurringCashFlow as RecurringCashFlowHDL
from scripts.lib.only_local import only_allow_local


def plot_risk_cones(ax, risk_cones):
    dates = np.array(risk_cones["dates"])
    means = np.array(risk_cones["means"])
    uppers = np.array(risk_cones["uppers"])
    lowers = np.array(risk_cones["lowers"])

    initial_value = risk_cones["initial_value"]

    ax.plot(dates, initial_value + means, label="Mean values")
    for it, data in enumerate(uppers):
        ax.plot(dates, initial_value + data, label=f"Upper cone {it}", linestyle="--")
    for it, data in enumerate(lowers):
        ax.plot(dates, initial_value + data, label=f"Lower cone {it}", linestyle="--")


def plot_account_value(ax, snapshots):
    dates, values = [], []
    for snapshot in snapshots:
        dates.append(snapshot.snapshot_time)
        # values.append(snapshot.hedged_value)
        values.append(snapshot.cashflows_npv)
    plt.plot(dates, values, label="Account value", color="black", linestyle=":")


def plot_values_and_risk_cones(ax, snapshots, risk_cones_by_date):
    dates, values = [], []
    for snapshot in snapshots:
        dates.append(snapshot.snapshot_time)
        values.append(snapshot.hedged_value)
        # values.append(snapshot.cashflow_npv)

        date = snapshot.snapshot_time.date()
        if date in risk_cones_by_date:
            risk_cones = risk_cones_by_date[date]
            rc_dates = np.array(risk_cones["dates"])
            # rc_means = np.array(risk_cones["means"])
            rc_uppers = np.array(risk_cones["uppers"])

            rc_lowers = np.array(risk_cones["lowers"])

            # ax.plot(rc_dates, snapshot.hedged_value + rc_means, label="Mean values")
            for it, data in enumerate(rc_uppers):
                ax.plot(rc_dates, snapshot.hedged_value + data, label=f"Upper cone {it}", linestyle="--")
            for it, data in enumerate(rc_lowers):
                ax.plot(rc_dates, snapshot.hedged_value + data, label=f"Lower cone {it}", linestyle="--")

    plt.plot(dates, values, label="Account value", color="black")


def run():
    from scripts.Test.utilities.CompanyScenario import CompanyScenario
    from main.apps.risk_metric.services.cashflow_risk_provider import CashFlowRiskService

    CompanyScenario.clean_old_companies_from_scenarios()

    start_date = Date.from_int(20200101)

    scenario = CompanyScenario(start_date=start_date)

    scenario.create_company(company_name="Test1", currency="EUR")
    scenario.create_account(company_name="Test1", account_name="A")

    # Add a recurring cashflow.
    cf1 = RecurringCashFlowHDL(currency=USD, amount=10000,
                               periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                               start_date=Date.from_int(20200101),
                               end_date=Date.from_int(20200601),
                               name="First Half")
    scenario.add_cashflow_to_account(name=("Test1", "A"), cashflow=cf1)

    # Add another recurring cashflow
    cf2 = RecurringCashFlowHDL(currency=USD, amount=-10000,
                               periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                               start_date=Date.from_int(20200601),
                               end_date=Date.from_int(20201231),
                               name="Second Half")
    scenario.add_cashflow_to_account(name=("Test1", "A"), cashflow=cf2)

    # Set account hedge settings.
    scenario.set_hedge_settings(name=("Test1", "A"),
                                custom={
                                    'VolTargetReduction': 0.95,
                                    'VaR95ExposureRatio': None,
                                    'VaR95ExposureWindow': None,
                                })


    d_days = 7

    risk_cones_by_date = {}

    for chunks in range(2):
        scenario.advance_to_first_business_date()
        current_date = scenario.get_current_date()

        cashflows_by_currency = scenario.get_cashflows_by_currency(company_name="Test1")
        try:
            risk_cones = CashFlowRiskService().get_cashflow_risk_cones(domestic="EUR",
                                                                       cashflows=cashflows_by_currency,
                                                                       start_date=current_date,
                                                                       end_date=current_date + 30)
            risk_cones_by_date[current_date.date()] = risk_cones
        except Exception as ex:
            pass

        # Advance the backtest.
        scenario.run_backtest_until(end_date=current_date + d_days)

    fig, ax = plt.subplots(figsize=(12, 8))
    snapshots = scenario.get_account_snapshots(name=("Test1", "A"))
    plot_values_and_risk_cones(ax, snapshots, risk_cones_by_date)

    ax.set_title("Risk cones over time.")
    ax.set_xlabel("Date")
    ax.set_ylabel("Values")
    fig.show()

    # scenario.full_clean_up()


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
