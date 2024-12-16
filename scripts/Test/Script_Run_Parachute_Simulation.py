import time
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from hdlib.Core.Currency import USD, JPY, MXN, EUR, CAD, GBP, INR, CHF, AUD
from hdlib.DateTime.Date import Date

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.DayCounter import DayCounter_HD
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)

# Number of days in a week.
days_week = 7


def plot_forwards_and_spot(start_date: Date, end_date: Date):
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.marketdata.services.fx.fx_provider import FxForwardProvider
    from main.apps.currency.models import FxPair

    fx_spot_provider = FxSpotProvider()
    fx_forward_provider = FxForwardProvider()

    point_values = fx_spot_provider.get_eod_spot_time_series(start_date=start_date, end_date=end_date,
                                                             fx_pair=(EUR, USD))
    # Turn the list of pairs "point_values" into a pair of lists.
    dates, values = zip(*point_values)

    EURUSD = FxPair.get_pair((EUR, USD))

    plt.figure(figsize=(12, 8))
    plt.plot(dates, values, label="Spot rates")

    # Make an HDL day counter
    dc = DayCounter_HD()

    last_date = None
    for date in dates:
        if last_date is not None and dc.days_between(last_date, date) < days_week:
            continue
        last_date = date
        logger.debug(f"Getting forward rates for {date}")
        days, values = fx_forward_provider.get_eod_forward_values(pair=(EUR, USD), date=date, time_as_days=True)
        fwd_dates = [date + day for day in days if day < 365]
        plt.plot(fwd_dates, values[:len(fwd_dates)], linestyle=":")  # , label=f"Forward rates for {date}"

    plt.title(f"Spot and forward rates for {EUR}/{USD}")
    plt.xlabel("Date")
    plt.ylabel("Rate")
    plt.legend()
    plt.show()


def plot_forward_pnls(account_id: int, start_date: Date, end_date: Date):
    # Get forward positions for account
    from main.apps.hedge.models.fxforwardposition import FxForwardPosition
    from main.apps.account.models.account import Account
    from main.apps.marketdata.services.fx.fx_provider import FxForwardProvider
    from main.apps.account.models import ParachuteCashFlow
    from main.apps.currency.models import FxPair

    account = Account.get_account(account_id)
    company = account.company

    max_fwds = 1

    # EURUSD = FxPair.get_pair((EUR, USD))

    plt.figure(figsize=(12, 8))

    # Get cashflows.
    # from main.apps.marketdata.services.universe_provider import UniverseProviderService

    # universe_provider = UniverseProviderService()
    # cashflows = ParachuteCashFlow.objects.filter(account=account, generation_time__gte=start_date,
    #                                              generation_time__lte=end_date)
    # for cashflow in cashflows:
    #     date = Date.from_datetime_date(cashflow.generation_time.date())
    #     dates, futures, npvs = [], [], []
    #     while date <= end_date:
    #         # Get a universe for this date.
    #         universe = universe_provider.make_universe(currencies={cashflow.currency, company.currency},
    #                                                    ref_date=date,
    #                                                    fx_pairs=(EURUSD,),
    #                                                    create_corr=False,
    #                                                    create_vols=False,
    #                                                    bypass_errors=True)
    #
    #         pricer = CashFlowPricer(universe=universe)
    #         future_cash, npv = pricer.pricing_breakdown(cashflow=cashflow, value_currency=USD)
    #
    #         dates.append(date)
    #         futures.append(future_cash)
    #         npvs.append(npv)
    #
    #         date += 1
    #
    #     plt.plot(dates, futures, label=f"Future cashflow for {cashflow}", color="red")
    #     plt.plot(dates, npvs, label=f"NPV for {cashflow}", color="black")
    # plt.legend()
    # plt.xlabel("Date")
    # plt.ylabel("Value (USD)")
    # plt.show()

    forward_positions = list(FxForwardPosition.objects.filter(account=account, enter_time__gte=start_date,
                                                              enter_time__lte=end_date))
    logger.debug(f"There are {len(forward_positions)} forward positions for account {account}.")
    # Find all dates on which there were forwards.
    all_dates = {}
    forwards_by_fx = {}
    for count, forward in enumerate(forward_positions):
        if count >= max_fwds:
            break
        forwards_by_fx.setdefault(forward.fxpair, []).append(forward)
        date = Date.from_datetime(forward.enter_time)
        end_time = Date.from_datetime(forward.unwind_time) if forward.unwind_time else end_date
        end_time = min(end_date, end_time)
        while date < end_time:
            all_dates.setdefault(forward.fxpair, set()).add(Date.from_datetime_date(date.date()))
            date += 1

    total_pnl_by_date = {}

    for fxpair, forwards in forwards_by_fx.items():
        logger.debug(f"Found {len(forwards)} forwards for {fxpair}.")
        logger.debug(f"Found {len(all_dates[fxpair])} dates for {fxpair}.")
        dates = all_dates[fxpair]

        # Get all forward curves that we need.
        forward_curves = {}
        for date in sorted(dates):
            logger.debug(f"  * Getting forward curve {fxpair} for date {date}")
            forward_curves[date] = FxForwardProvider().get_forward_curve(pair=fxpair, date=date)

        for count, forward in enumerate(forwards):
            logger.debug(f"Forward position {forward}")
            # Get forward rates for forward
            date = Date.from_datetime(forward.enter_time)
            end_time = Date.from_datetime(forward.unwind_time) if forward.unwind_time else end_date
            end_time = min(end_date, end_time)
            fwd_dates, fwd_pnls, spot_values, fwd_points = [], [], [], []
            while date < end_time:
                logger.debug(f"  * Computing PnL for forward at date: {date}")
                ref_date = Date.from_datetime_date(date.date())
                forward_curve = forward_curves[ref_date]
                spot_rate = forward_curve.spot()
                spot_pnl = (spot_rate - forward.initial_spot_price) * forward.amount
                current_fwd_rate = forward_curve.at_D(forward.delivery_time)

                fwd_pnts = current_fwd_rate - spot_rate
                fwd_points_pnl = (fwd_pnts - forward.initial_fwd_points) * forward.amount
                pnl = forward.compute_pnl(current_fwd_rate)

                fwd_dates.append(date)
                fwd_pnls.append(pnl)
                spot_values.append(spot_pnl)
                fwd_points.append(fwd_points_pnl)

                total_pnl_by_date.setdefault(ref_date, 0.)
                total_pnl_by_date[ref_date] += pnl

                date += 1
            # plt.plot(fwd_dates, fwd_pnls)  # , label=f"Forward PnL for {forward}")

            fwd_dates = np.array(fwd_dates)
            fwd_pnls = np.array(fwd_pnls)
            spot_values = np.array(spot_values)
            fwd_points = np.array(fwd_points)

            plt.plot(fwd_dates, spot_values, color=f"C{count}", linestyle=":")
            plt.plot(fwd_dates, fwd_pnls, color=f"C{count}")

    # Plot total PnLs.
    if 0 < len(total_pnl_by_date):
        dates, pnls = zip(*sorted(total_pnl_by_date.items()))
        plt.plot(dates, pnls, label=f"Total PnLs for account {account}", linestyle="--", color="black")

    from main.apps.hedge.models import ParachuteRecordAccount

    # ========================================================================================================
    # NOTE(Nate): This will only plot well if there is only one bucket, which is the case I'm looking at.
    # ========================================================================================================

    bucketed_parachute_records = ParachuteRecordAccount.get_in_range_bucketed(account=account)
    it = -1
    for bucket, parachute_records in bucketed_parachute_records.items():
        it += 1
        parachute_records = sorted(parachute_records, key=lambda x: x.time)
        times = [x.time for x in parachute_records]

        account_values = [x.bucket_value for x in parachute_records]
        unhedged_values = [x.cashflows_npv for x in parachute_records]
        adjusted_limit_values = [x.adjusted_limit_value for x in parachute_records]

        initial_value = account_values[0]
        account_values = [x - initial_value for x in account_values]
        unhedged_values = [x - initial_value for x in unhedged_values]
        account_pnl = [x - y for x, y in zip(account_values, unhedged_values)]

        hedge_points = [(x.time, x.bucket_value - initial_value) for x in parachute_records if
                        x.fraction_to_hedge != 0]
        # Turn the vector of pairs, hedge_points, into a pair of vectors.
        hedge_times, hedge_values = zip(*hedge_points)

        plt.plot(times, account_values, label=f"Account value ({bucket})", color=f"C{it}")  # marker="o",
        plt.plot(times, unhedged_values, label=f"Unhedged value ({bucket})", color=f"C{it}", linestyle=":")
        plt.plot(times, account_pnl, label=f"Account PnL ({bucket})", color=f"gray", linestyle="--")
        plt.plot(times, adjusted_limit_values, linestyle="--", color=f"C{it}")
        plt.scatter(hedge_times, hedge_values)

    plt.title(f"Forward PnLs for account {account}")
    plt.xlabel("Date")
    plt.ylabel("PnL")
    plt.legend()
    plt.show()


def plot_parachute(account):
    from main.apps.hedge.models import ParachuteRecordAccount
    from main.apps.account.models import Account

    account = Account.get_account(account)

    bucketed_parachute_records = ParachuteRecordAccount.get_in_range_bucketed(account=account)

    plt.figure(figsize=(12, 8))

    it = -1
    for bucket, parachute_records in bucketed_parachute_records.items():
        it += 1

        times = [x.time for x in parachute_records]
        volatilities = [x.volatility for x in parachute_records]
        probabilities = [x.p_no_breach for x in parachute_records]

        account_values = [x.bucket_value for x in parachute_records]
        complete_account_values = [x.complete_bucket_value for x in parachute_records]
        unhedged_values = [x.cashflows_npv for x in parachute_records]
        adjusted_limit_values = [x.adjusted_limit_value for x in parachute_records]

        limit_value = parachute_records[0].adjusted_limit_value

        hedge_points = [(x.time, x.bucket_value) for x in parachute_records if x.fraction_to_hedge != 0]
        # Turn the vector of pairs, hedge_points, into a pair of vectors.
        hedge_times, hedge_values = zip(*hedge_points)

        plt.plot(times, account_values, label=f"Account value ({bucket})", color=f"C{it}", linestyle="--")
        plt.plot(times, complete_account_values, label=f"Complete account value ({bucket})", color=f"C{it}")
        plt.plot(times, unhedged_values, label=f"Unhedged value ({bucket})", color=f"C{it}", linestyle=":")
        plt.plot(times, adjusted_limit_values, linestyle="--", color=f"C{it}")
        plt.scatter(hedge_times, hedge_values)

    plt.title(f"Account value over time for account {account} ({account})")
    plt.xlabel("Date")
    plt.ylabel("Value in domestic")
    plt.legend()
    plt.show()

    # Plot probability of breach and percent hedged.

    # fig, (ax0, ax1, ax2) = plt.subplots(3, sharex=True, figsize=(12, 6))
    # fig.suptitle('Fraction hedged and probability of breach')
    #
    # ax0.plot(times, probabilities, color="black")
    # ax0.set_title("Probability no breach")
    # ax1.plot(times, fractions, color="blue")
    # ax1.set_title("Fraction hedged")
    # ax2.plot(times, volatilities, color="red")
    # ax2.set_title("Volatility")
    # fig.show()


# noinspection DuplicatedCode
def clean_hedging_related(company_name):
    from main.apps.hedge.models import FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest
    from main.apps.account.models import Account, CashFlow
    from main.apps.history.models import AccountSnapshot, CompanySnapshot
    from main.apps.hedge.models.company_fxposition import CompanyFxPosition
    from main.apps.history.models import ReconciliationRecord
    from main.apps.hedge.models import CompanyEvent
    from main.apps.hedge.models.fxforwardposition import FxForwardPosition
    from main.apps.hedge.models.parachute_spot_positions import ParachuteSpotPositions
    from main.apps.account.models.parachute_data import ParachuteData
    from main.apps.events.models import CashflowRolloff, ForwardSettlement
    from main.apps.hedge.models import ParachuteRecordAccount
    from main.apps.account.models.parachute_cashflow import ParachuteCashFlow

    accounts = Account.get_account_objs(company=company_name)

    # company = None
    for account in accounts:
        if account is None:
            continue
        company = account.company

        FxPosition.objects.filter(account=account).delete()
        CompanyFxPosition.objects.filter(company=company).delete()
        FxForwardPosition.objects.filter(account=account).delete()
        ParachuteData.objects.filter(account=account).delete()

        CashFlow.objects.filter(account=account).delete()

        CompanyEvent.objects.filter(company=account.company).delete()
        CompanyHedgeAction.objects.filter(company=company).delete()
        AccountHedgeRequest.objects.filter(account=account).delete()
        ReconciliationRecord.objects.filter(company=company).delete()
        OMSOrderRequest.objects.filter(company_hedge_action__company=company).delete()

        CompanySnapshot.objects.filter(company=company).delete()
        AccountSnapshot.objects.filter(account=account).delete()

        CashflowRolloff.objects.filter(parent_cashflow__account__company=company).delete()
        ForwardSettlement.objects.filter(parent_forward__cashflow__account__company=company).delete()

        ParachuteRecordAccount.objects.filter(parachute_account=account).delete()
        ParachuteSpotPositions.objects.filter(parachute_account=account).delete()
        ParachuteCashFlow.objects.filter(account=account).delete()


def setup_company_parachute_forward_config(company):
    from main.apps.oems.models.parachute_forward_configuration import ParachuteForwardConfiguration
    from main.apps.currency.models import FxPair

    EURUSD = FxPair.get_pair("EURUSD")
    GBPUSD = FxPair.get_pair("GBPUSD")
    USDCAD = FxPair.get_pair("USDCAD")
    CADUSD = FxPair.get_pair("CADUSD")
    ParachuteForwardConfiguration.add_config(company=company, fxpair=EURUSD, min_order_size=10_000,
                                             use_multiples=True)
    ParachuteForwardConfiguration.add_config(company=company, fxpair=GBPUSD, min_order_size=10_000,
                                             use_multiples=True)
    ParachuteForwardConfiguration.add_config(company=company, fxpair=USDCAD, min_order_size=10_000,
                                             use_multiples=True)
    ParachuteForwardConfiguration.add_config(company=company, fxpair=CADUSD, min_order_size=10_000,
                                             use_multiples=True)


def recreate_test(company_name):
    from main.apps.account.models import Company, Account, CashFlow
    from main.apps.hedge.models import HedgeSettings
    from main.apps.account.models.parachute_data import ParachuteData

    pangea_paper_company = Company.create_company(company_name, currency=USD)

    account = Account.get_or_create_account(name="High",
                                            company=pangea_paper_company,
                                            account_type=Account.AccountType.DEMO)
    logger.debug(f"Account {account} has id {account.id}")
    # Set up the account as a parachute account.
    account.strategy = Account.AccountStrategy.PARACHUTE
    account.save()

    # ==========================================================================================================
    # Set parachute forward configuration.
    # ==========================================================================================================

    setup_company_parachute_forward_config(pangea_paper_company)

    # ==========================================================================================================
    # Create the parachute configuration
    # ==========================================================================================================

    lower_limit = 0.03
    ParachuteData.create_for_account(account, lower_p=0.97, upper_p=0.99, lower_limit=lower_limit,
                                     floating_pnl_fraction=0.0)
    logger.debug(f"Set the lower value for the account to be {lower_limit}.")

    # ==========================================================================================================
    #   Create cashflows
    # ==========================================================================================================

    def create_month(exp, sign=-1):
        CashFlow.create_cashflow(account=account, date=exp,
                                 currency=CAD, amount=-1000000,
                                 roll_convention=CashFlow.RollConvention.NEAREST,
                                 status=CashFlow.CashflowStatus.ACTIVE)
        # CashFlow.create_cashflow(account=account, date=exp,
        #                          currency=EUR, amount=-7_114_147 * sign,
        #                          roll_convention=CashFlow.RollConvention.NEAREST,
        #                          status=CashFlow.CashflowStatus.ACTIVE)
        # CashFlow.create_cashflow(account=account, date=exp,
        #                          currency=CAD, amount=-2_640_800 * sign,
        #                          roll_convention=CashFlow.RollConvention.NEAREST,
        #                          status=CashFlow.CashflowStatus.ACTIVE)
        # CashFlow.create_cashflow(account=account, date=exp,
        #                          currency=GBP, amount=1_838_236 * sign,
        #                          roll_convention=CashFlow.RollConvention.NEAREST,
        #                          status=CashFlow.CashflowStatus.ACTIVE)
        # CashFlow.create_cashflow(account=account, date=exp,
        #                          currency=AUD, amount=-476_894 * sign,
        #                          roll_convention=CashFlow.RollConvention.NEAREST,
        #                          status=CashFlow.CashflowStatus.ACTIVE)

    # create_month(Date.create(ymd=2021_01_31, hour=9))  # 2021_01_29
    # create_month(Date.create(ymd=2021_02_28, hour=9))  # 2021_02_26
    create_month(Date.create(ymd=2022_03_28, hour=9))  # 2022_03_31
    create_month(Date.create(ymd=2022_03_29, hour=9))  # 2022_03_31
    create_month(Date.create(ymd=2022_04_28, hour=9))  # 2022_04_30
    create_month(Date.create(ymd=2022_04_29, hour=9))  # 2022_04_30
    # create_month(Date.create(ymd=2022_05_28, hour=9))  # 2022_05_31
    # create_month(Date.create(ymd=2022_05_29, hour=9))  # 2022_05_31
    # create_month(Date.create(ymd=2022_06_28, hour=9))  # 2022_06_30
    # create_month(Date.create(ymd=2022_06_29, hour=9))  # 2022_06_30
    # create_month(Date.create(ymd=2022_07_28, hour=9))  # 2022_07_30
    # create_month(Date.create(ymd=2022_07_29, hour=9))  # 2022_07_30
    # create_month(Date.create(ymd=2022_08_28, hour=9))  # 2022_08_31
    # create_month(Date.create(ymd=2022_08_29, hour=9))  # 2022_08_31
    # create_month(Date.create(ymd=2022_09_28, hour=9))  # 2022_09_30
    # create_month(Date.create(ymd=2022_09_29, hour=9))  # 2022_09_30
    # create_month(Date.create(ymd=2022_10_28, hour=9))  # 2022_10_29
    # create_month(Date.create(ymd=2022_10_29, hour=9))  # 2022_10_29
    # create_month(Date.create(ymd=2022_11_28, hour=9))  # 2022_11_30
    # create_month(Date.create(ymd=2022_11_29, hour=9))  # 2022_11_30
    # create_month(Date.create(ymd=2022_12_28, hour=9))  # 2022_12_31
    # create_month(Date.create(ymd=2022_12_29, hour=9))  # 2022_12_31

    # Set or update hedge settings.
    # NOTE: This account should not do a min var hedge since it is a parachute account.
    HedgeSettings.create_or_update_settings(account=account,
                                            max_horizon_days=7300,
                                            margin_budget=2.e10,
                                            # Hard limit account still min-var hedges.
                                            method="MIN_VAR",
                                            custom={
                                                'VolTargetReduction': 0.1,
                                                'VaR95ExposureRatio': None,
                                                'VaR95ExposureWindow': None,
                                            })

    logger.debug("Created settings for account")
    logger.debug("\n")

    return account


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

    pangea_paper_company = Company.get_company(company="ReverseBob")

    account = Account.get_or_create_account(name="High",
                                            company=pangea_paper_company,
                                            account_type=Account.AccountType.DEMO)

    SnapshotVisualizationService().create_realized_variance_figure(account=account).show()
    SnapshotVisualizationService().create_accounts_values_figure(company=pangea_paper_company).show()
    SnapshotVisualizationService().create_accounts_risk_reduction_figure(company=pangea_paper_company).show()


def run():
    start_date = Date.create(year=2022, month=3, day=1, hour=23)
    end_date = start_date + 15

    company_to_run = "ReverseBob"
    clean_hedging_related(company_to_run)

    # Set up the company (if it is not set up) and return the account that we are testing with.
    account = recreate_test(company_to_run)

    # Run the simulation.
    run_for_company(company_name=company_to_run, start_date=start_date, end_date=end_date)

    # Plot the results, from a parachute point of view.
    try:
        plot_parachute(account)
    except Exception as e:
        pass

    return account


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

    account = run()
    logger.debug(f"Account for run: {account}.")
