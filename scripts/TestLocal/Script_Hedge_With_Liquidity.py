import time
from typing import Optional

import numpy as np

from hdlib.Core.Currency import USD, GBP, AUD, JPY
from hdlib.DateTime.Date import Date

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)

# Number of days in a week.
days_week = 7


# noinspection DuplicatedCode
def clean_hedging_related():
    from main.apps.hedge.models import FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest
    from main.apps.account.models import Account, CashFlow
    from main.apps.history.models import AccountSnapshot, CompanySnapshot
    from main.apps.hedge.models.company_fxposition import CompanyFxPosition
    from main.apps.history.models import ReconciliationRecord
    from main.apps.hedge.models import CompanyEvent
    from main.apps.hedge.models.fxforwardposition import FxForwardPosition

    accounts = [Account.get_account(name=("PangeaPaper", "High Hedge")),
                Account.get_account(name=("PangeaPaper", "Low Hedge"))]

    company = None
    for account in accounts:
        if account is None:
            continue
        company = account.company

        FxPosition.objects.filter(account=account).delete()
        CompanyFxPosition.objects.filter(company=company).delete()
        FxForwardPosition.objects.filter(account=account).delete()

        CashFlow.objects.filter(account=account).delete()

        CompanyEvent.objects.filter(company=account.company).delete()
        CompanyHedgeAction.objects.filter(company=company).delete()
        AccountHedgeRequest.objects.filter(account=account).delete()
        ReconciliationRecord.objects.filter(company=company).delete()
        OMSOrderRequest.objects.filter(company_hedge_action__company=company).delete()

        CompanySnapshot.objects.filter(company=company).delete()
        AccountSnapshot.objects.filter(account=account).delete()

    if company:
        company.delete()


def set_up_company(start_date: Date, include_broker: bool = False, company_name="PangeaPaper"):
    from main.apps.account.models import Company, Account, CashFlow
    from main.apps.hedge.models import HedgeSettings
    from main.apps.account.models import Broker, BrokerAccount

    pangea_paper_company = Company.create_company(company_name, currency=USD)

    try:
        Account.remove_account(account_name="PaperTrading", company=pangea_paper_company)
    except Exception:
        pass

    account_high = Account.get_or_create_account(name="High Hedge",
                                                 company=pangea_paper_company,
                                                 account_type=Account.AccountType.DEMO)
    logger.debug(f"Account {account_high} has id {account_high.id}")

    account_low = Account.get_or_create_account(name="Low Hedge",
                                                company=pangea_paper_company,
                                                account_type=Account.AccountType.DEMO)
    logger.debug(f"Account {account_low} has id {account_low.id}")

    if include_broker:
        status, broker = Broker.create_broker(name="IBKR")
        BrokerAccount.delete_company_accounts(company=pangea_paper_company)
        status, broker_account = BrokerAccount.create_account_for_company(company=pangea_paper_company,
                                                                          broker=broker,
                                                                          broker_account_name="DU5241179",
                                                                          account_type=BrokerAccount.AccountType.LIVE)
        logger.debug(status)

    end_days = 30

    CashFlow.create_cashflow(account=account_high, date=start_date + end_days,
                             end_date=start_date + end_days,
                             currency=GBP, amount=-230_000, name="R1",
                             status=CashFlow.CashflowStatus.ACTIVE)

    CashFlow.create_cashflow(account=account_low, date=start_date + end_days,
                             currency=GBP, amount=498_000, name="R1",
                             status=CashFlow.CashflowStatus.ACTIVE)

    # Set or update hedge settings.
    HedgeSettings.create_or_update_settings(account=account_high,
                                            max_horizon_days=365,
                                            margin_budget=2.e10,
                                            method="MIN_VAR",
                                            custom={
                                                'VolTargetReduction': 0.85,
                                                'VaR95ExposureRatio': None,
                                                'VaR95ExposureWindow': None,
                                            })

    HedgeSettings.create_or_update_settings(account=account_low,
                                            max_horizon_days=365,
                                            margin_budget=2.e10,
                                            method="MIN_VAR",
                                            custom={
                                                'VolTargetReduction': 0.25,
                                                'VaR95ExposureRatio': None,
                                                'VaR95ExposureWindow': None,
                                            })

    # HedgeSettings.create_or_update_settings(account=account,
    #                                         margin_budget=2.e10,
    #                                         method="PERFECT",
    #                                         custom={'UniformRatio': 1.0})

    logger.debug("Created settings for account")
    logger.debug("\n")


def plot_for_multilevel(company_name: str):
    from main.apps.account.models import Company
    from main.apps.account.models.account import Account
    from main.apps.history.services.visualization import SnapshotVisualizationService

    company = Company.get_company(company_name)

    all_accounts = Account.get_account_objs(company=company)

    # ================================
    # Plot values of all accounts.
    # ================================

    fig = SnapshotVisualizationService().create_accounts_values_figure(company=company)
    fig.show()

    # ================================
    # Plot risk reduction
    # ================================

    fig = SnapshotVisualizationService().create_accounts_risk_reduction_figure(company=company)
    fig.show()

    for account in Account.get_account_objs(company=company):
        SnapshotVisualizationService().create_account_allocation_plot(account=account).show()
        SnapshotVisualizationService().create_liquidity_pool_utilization_figure(account).show()


def run():
    start_date = Date.create(year=2021, month=4, day=5, hour=23)
    end_date = start_date + 5

    company_to_run = "PangeaPaper"
    clean_hedging_related()
    set_up_company(start_date=start_date, company_name=company_to_run)

    run_for_company(company_name=company_to_run, start_date=start_date, end_date=end_date)


def run_for_company(company_name: str, start_date: Date, end_date: Date):
    from main.apps.account.models import Company
    from main.apps.hedge.services.eod_and_intra import EodAndIntraService
    from main.apps.oems.services.order_service import OrderService
    from main.apps.hedge.models import CompanyHedgeAction
    from main.apps.hedge.services.hedge_position import HedgePositionService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.account.models.account import Account
    from main.apps.history.services.snapshot import SnapshotProvider

    company = Company.get_company(company_name)
    logger.debug(f"Running for Company: {company.name}")

    # If the OMS is not ready for you to complete EOD, wait this long.
    retry_time = 15
    snapshot_provider = SnapshotProvider()

    date = start_date
    it = 1
    while date <= end_date:
        # TODO: Check for holidays other than weekends?
        while date.day_of_week() in {6, 7}:
            date += 1

        if end_date < date:
            break

        logger.debug(f"Starting simulation of day {date} (day {it}).")

        def print_company_positions(time: Date):
            # Company's current positions.
            company_positions = HedgePositionService().get_positions_for_company_by_account(company=company,
                                                                                            time=time)

            cache = FxSpotProvider().get_eod_spot_fx_cache(date=date)
            if len(company_positions) == 0:
                print("NO POSITIONS!")
            for account, positions in company_positions.items():
                print(f"Account \"{account.name}\":")
                for position in positions:
                    # if position.amount != 0:
                    print(f"\t{position.fxpair}: {position.amount}, "
                          f"Px0 = {np.sign(position.amount) * position.total_price}, "
                          f"PxT = {cache.position_value(position)}, "
                          f"FX = {cache.get_fx(position.fxpair)}")

        start_time = Date.now()

        logger.debug(f"Starting EOD flow for {company} at simulated time {date}")
        logger.debug(f"Company positions:")
        print_company_positions(date)
        status = EodAndIntraService(date).start_eod_flow_for_company(time=date, company=company)
        logger.debug(f"Done starting EOD flow for {company}, status: {status}")
        if not status.is_error():
            logger.debug(f"Ending EOD flow for {company}")

            company_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company)
            logger.debug(f"Last company hedge action was id = {company_hedge_action.id}.")

            if Account.has_live_accounts(company=company):
                while not OrderService.are_company_orders_done(company=company):
                    logger.debug(
                        f"Waiting for OMS to fill orders for {company.name}. "
                        f"Waiting {retry_time} seconds...")
                    time.sleep(retry_time)
            logger.debug(f"Orders filled for {company.name}. Ready to continue.")

            # Some time went by waiting for the orders to fill.
            ready_for_end_time = Date.now()
            diff = ready_for_end_time - start_time
            date_end_time = date + diff

            logger.debug(f"Ending EOD flow for {company} at simulated time {date_end_time}")
            status = EodAndIntraService(date_end_time).end_eod_flow_for_company(time=date_end_time, company=company)
            logger.debug(f"Ended EOD flow for company. Status was: {status}")
            logger.debug(f"Final positions:")
            print_company_positions(date_end_time)

        else:
            logger.error(f"Status was error from starting EOD flow: {status}")

        # Don't keep simulating if there are errors.
        if status.is_error():
            logger.error(f"Status was error. Not continuing simulation.")
            break

        logger.debug(f"Ending simulation of day {date}.\n\n")
        # Go to the next date.
        date += 1
        it += 1

    logger.debug("Done with RUNNING.")

    for account in Account.get_active_accounts(live_only=False, company=company):
        logger.debug(f"Stats for account: {account.name}\n")
        stats = snapshot_provider.get_account_summary_stats(account=account, start_date=start_date, end_date=end_date)
        logger.debug(stats)

    # plotting(start_date, end_date)
    plot_for_multilevel(company_name=company_name)


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
