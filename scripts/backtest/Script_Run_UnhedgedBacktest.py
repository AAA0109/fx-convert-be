import os
import sys
import random

from matplotlib import pyplot as plt
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def run():
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    from scripts.backtest.utils.CompanyConfigurer import CompanyConfigurer
    from scripts.backtest.utils.UnhedgedBacktester import UnhedgedBacktester

    # =========================
    # Configure the company / accounts / cashflows
    # =========================
    cashflows_fpath = "/Users/nathaniel/Pangea/client-data/bible-project/BibleProject_6_30_2022_shifted_mini.csv"
    company_name = "BibleProject"

    configurer = CompanyConfigurer(base_company_name=company_name,
                                   cashflows_fpath=cashflows_fpath,
                                   ignore_unsupported_currencies=True,
                                   ignore_cashflow_currencies=["SEK", "NOK"],
                                   are_cashflows_annualized=True)
    companies = configurer.configure_companies(clean_existing=True)

    # =========================
    # Run the Backtest
    # =========================

    base_dir = "/Users/nathaniel/Pangea/client-data/bible-project/out/"
    try:
        os.mkdir(base_dir)
    except Exception:
        pass

    start_date = Date.create(year=2021, month=1, day=4, hour=23)
    end_date = start_date + 365

    directory = "/Users/nathaniel/Pangea/output/unhedged-backtest/"
    unhedged_backtester = UnhedgedBacktester(company=companies[0])
    unhedged_backtester.stylized_run(start_date=start_date, end_date=end_date, num_samples=1000)
    # Save data.
    unhedged_backtester.save_simulation_to_directory(directory)
    summary = unhedged_backtester.create_summary()
    summary.to_csv(f"{directory}/summary.csv")
    # Create plots.
    create_plots(unhedged_backtester)


def create_plots(unhedged_backtester):
    account = unhedged_backtester.accounts[0]
    percentiles = [0.005, 0.05, 0.25, 0.5, 0.75, 0.95, 0.995]

    # unhedged_backtester = UnhedgedBacktester.load_simulation_from_directory(
    #     dirpath="/Users/nathaniel/Pangea/output/unhedged-backtest")
    # account = unhedged_backtester.accounts[0]

    plt.figure(figsize=(12, 10))

    perc = unhedged_backtester.compute_percentiles(percentiles, account)
    colors = ["lightgray", "darkgray", "gray"]

    random.seed(4)
    indices = list(range(unhedged_backtester.num_samples))
    random.shuffle(indices)

    for it, index in enumerate(indices):
        cindex = 0 if it < 0.9 * unhedged_backtester.num_samples else \
            1 if it < 0.975 * unhedged_backtester.num_samples else 2
        plt.plot(unhedged_backtester.get_total_value_trajectory(index, account), linewidth=0.4, color=colors[cindex])

    for p, pv in zip(perc, percentiles):
        plt.plot(p, label=f"Percentile: {100 * pv:0.3f}")

    plt.xlabel("Day")
    plt.ylabel("Account value")
    plt.title(f"Scenario outcomes and percentiles for {account}")
    plt.legend()
    plt.show()


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
