import os
import sys
import random

from matplotlib import pyplot as plt
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.HedgeAccount import HedgeMethod
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def run():
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    from scripts.backtest.utils.CompanyConfigurer import CompanyConfigurer
    from scripts.backtest.utils.Backtester import Backtester

    # =========================
    # Configure the company / accounts / cashflows
    # =========================
    # cashflows_fpath = r"C:\Users\jkirk\OneDrive\LARS\HedgeDesk\ClientData\BibleProject_6_30_2022_shifted_mini.csv"
    cashflows_fpath = r"/Users/nathaniel/Pangea/client-data/bible-project/BibleProject_6_30_2022_shifted_mini.csv"
    company_name = "BibleProject"
    run_backtest = True

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

    start_date = Date.create(year=2022, month=4, day=29, hour=23)
    end_date = start_date + 60

    backtester = Backtester(test_name=company_name, companies=companies, base_dir=base_dir)

    if run_backtest:
        backtester.run(start_date=start_date,
                       end_date=end_date)
    backtester.generate_summary_package(start_date=start_date, end_date=end_date)
    # backtester.output_snapshots(start_date=start_date, end_date=end_date)


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
