"""
Simulate the whole hedging flow.

Run POEMS with the command:
    gunicorn --certfile=poems/etc/cert.pem --keyfile=poems/etc/key.pem -b 127.0.0.1:10000 --workers=1 --threads=1 --log-level=debug poems.main_oems:app

"""
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
def clean_hedging_related(name: Optional[str] = None):
    from main.apps.hedge.models import FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest
    from main.apps.account.models import Account, CashFlow
    from main.apps.history.models import AccountSnapshot, CompanySnapshot
    from main.apps.hedge.models.company_fxposition import CompanyFxPosition
    from main.apps.history.models import ReconciliationRecord
    from main.apps.hedge.models import CompanyEvent
    from main.apps.hedge.models.fxforwardposition import FxForwardPosition

    if name and name == "ManyLevelCompany":
        accounts = Account.get_account_objs(company="ManyLevelCompany")
    elif name and name == "PangeaPaper":
        accounts = [Account.get_account(name=("PangeaPaper", "PaperTrading"))]
    else:
        accounts = []

    company = None
    for account in accounts:
        if account is None:
            continue
        company = account.company

        FxPosition.objects.filter(account=account).delete()
        CompanyFxPosition.objects.filter(company=company).delete()

        FxForwardPosition.objects.filter(cashflow__account=account).delete()
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
    from main.apps.hedge.models.fxforwardposition import FxForwardPosition
    from main.apps.currency.models import FxPair, Currency
    from main.apps.marketdata.services.universe_provider import UniverseProviderService

    pangea_paper_company = Company.create_company(company_name, currency=USD)

    try:
        Account.remove_account(account_name="PaperTrading", company=pangea_paper_company)
    except Exception:
        pass

    account = Account.get_or_create_account(name="PaperTrading",
                                            company=pangea_paper_company,
                                            account_type=Account.AccountType.DEMO)
    logger.debug(f"Account {account} has id {account.id}")

    if include_broker:
        status, broker = Broker.create_broker(name="IBKR")
        BrokerAccount.delete_company_accounts(company=pangea_paper_company)
        status, broker_account = BrokerAccount.create_account_for_company(company=pangea_paper_company,
                                                                          broker=broker,
                                                                          broker_account_name="DU5241179",
                                                                          account_type=BrokerAccount.AccountType.LIVE)
        logger.debug(status)

    # periodicity = "WEEKLY:Mon:Tue:Wed:Thu:Fri"
    # periodicity = "WEEKLY:Fri"
    # RecurringCashflow.create_cashflow(account=account,
    #                                   start_date=start_date,
    #                                   end_date=start_date + days_week * 10,
    #                                   currency=GBP,
    #                                   amount=100,
    #                                   periodicity=periodicity)

    # CashFlow.create_cashflow(account=account, date=start_date + 50, currency=GBP, amount=10000, name="Test",
    #                          status=CashFlow.CashflowStatus.ACTIVE)

    start_days = 0
    end_days = 180  # 2 * 365

    CashFlow.create_cashflow(account=account, date=start_date + start_days,
                             end_date=start_date + end_days,
                             currency=GBP, amount=10_000, name="R1",
                             periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=FR",
                             status=CashFlow.CashflowStatus.ACTIVE)
    CashFlow.create_cashflow(account=account, date=start_date + start_days,
                             end_date=start_date + end_days,
                             currency=AUD, amount=-12_000, name="R2",
                             periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                             status=CashFlow.CashflowStatus.ACTIVE)
    CashFlow.create_cashflow(account=account, date=start_date + start_days,
                             end_date=start_date + end_days,
                             currency=JPY, amount=-40_000, name="R3",
                             periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=MO",
                             status=CashFlow.CashflowStatus.ACTIVE)

    CashFlow.create_cashflow(account=account, date=start_date + 10,
                             end_date=start_date + end_days,
                             currency=AUD, amount=100_000, name="Big",
                             periodicity="FREQ=MONTHLY;INTERVAL=1;COUNT=10",
                             status=CashFlow.CashflowStatus.ACTIVE)

    # Create a universe so we can "enter forwards" at the correct rate.
    usd = Currency.get_currency("USD")
    fx_pairs = FxPair.get_foreign_to_domestic_pairs(domestic=usd)
    universe = UniverseProviderService().make_cntr_currency_universe(domestic=usd,
                                                                     ref_date=start_date,
                                                                     bypass_errors=True,
                                                                     fx_pairs=fx_pairs)

    count = 0
    for cashflow in CashFlow.get_company_cashflows(company=pangea_paper_company):
        # Hedge with forwards
        for it, cf in enumerate(cashflow.get_hdl_cashflows()):
            try:
                fxpair = FxPair.get_pair_from_currency(cf.currency, USD)
                fwd_rate = universe.get_forward(fxpair, cf.pay_date)
                spot_rate = universe.get_spot(fxpair)
                FxForwardPosition.add_forward_to_account(cashflow=cashflow,
                                                         delivery_time=cf.pay_date,
                                                         amount=-cf.amount,
                                                         enter_time=start_date,
                                                         fxpair=fxpair,
                                                         forward_price=fwd_rate,
                                                         spot_price=spot_rate)
                count += 1
            except Exception:
                pass
    logger.debug(f"Added {count} forwards.")

    # Set or update hedge settings.
    HedgeSettings.create_or_update_settings(account=account,
                                            max_horizon_days=365,
                                            margin_budget=2.e10,
                                            method="MIN_VAR",
                                            custom={
                                                'VolTargetReduction': 0.95,
                                                'VaR95ExposureRatio': None,
                                                'VaR95ExposureWindow': None,
                                            })

    # HedgeSettings.create_or_update_settings(account=account,
    #                                         margin_budget=2.e10,
    #                                         method="PERFECT",
    #                                         custom={'UniformRatio': 1.0})

    logger.debug("Created settings for account")
    logger.debug("\n")


def create_account_with_varying_risk_reductions(start_date: Date, company_name="ManyLevelCompany"):
    from main.apps.account.models import Company, Account, CashFlow
    from main.apps.hedge.models import HedgeSettings

    # Create company
    many_level_company = Company.create_company(company_name, currency=USD)
    # Delete existing accounts.
    all_account = Account.get_account_objs(company=many_level_company)
    for account in all_account:
        account.delete()

    dlevel = 10
    levels = range(0, 100 + dlevel, dlevel)
    for level in levels:
        account = Account.get_or_create_account(name=f"Level_{level}",
                                                company=many_level_company,
                                                account_type=Account.AccountType.DEMO)

        CashFlow.create_cashflow(account=account, date=start_date + 7,
                                 end_date=start_date + 365,
                                 currency=GBP, amount=10000, name="R1",
                                 periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=FR",
                                 status=CashFlow.CashflowStatus.ACTIVE)
        CashFlow.create_cashflow(account=account, date=start_date,
                                 end_date=start_date + 365,
                                 currency=AUD, amount=-12000, name="R2",
                                 periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                                 status=CashFlow.CashflowStatus.ACTIVE)

        date = start_date.first_of_next_month()
        while date < start_date + 365:
            CashFlow.create_cashflow(account=account, date=date,
                                     currency=AUD, amount=80000,
                                     status=CashFlow.CashflowStatus.ACTIVE)
            date = date.first_of_next_month()

        # Set or update hedge settings.
        target = level / 100.0
        HedgeSettings.create_or_update_settings(account=account,
                                                margin_budget=2.e10,
                                                method="MIN_VAR",
                                                custom={
                                                    'VolTargetReduction': target,
                                                    'VaR95ExposureRatio': None,
                                                    'VaR95ExposureWindow': None,
                                                })


def plot_for_multilevel(company_name: str, start_date: Optional[Date] = None, end_date: Optional[Date] = None):
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


def plotting(start_date: Optional[Date] = None, end_date: Optional[Date] = None):
    from main.apps.account.models import Company
    from main.apps.account.models.account import Account
    from main.apps.history.services.visualization import SnapshotVisualizationService

    pangea_paper_company = Company.get_company(company="PangeaPaper")

    account = Account.get_or_create_account(name="PaperTrading",
                                            company=pangea_paper_company,
                                            account_type=Account.AccountType.DEMO)

    SnapshotVisualizationService().create_realized_variance_figure(account=account).show()
    SnapshotVisualizationService().create_accounts_values_figure(company=pangea_paper_company).show()
    SnapshotVisualizationService().create_accounts_risk_reduction_figure(company=pangea_paper_company).show()


def run():
    start_date = Date.create(year=2021, month=4, day=5, hour=23)
    end_date = start_date + 30

    do_multi_level = False
    if do_multi_level:
        company_to_run = "ManyLevelCompany"
        clean_hedging_related(company_to_run)
        create_account_with_varying_risk_reductions(start_date=start_date, company_name=company_to_run)
    else:
        do_broker = True
        if do_broker:
            company_to_run = "PangeaPaper"
        else:
            company_to_run = "PangeaPaper_NoBroker"
        clean_hedging_related(company_to_run)
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
    plot_for_multilevel(company_name=company_name, start_date=start_date, end_date=end_date)


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
