import os
import random
import sys
from datetime import timedelta
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.Core.Currency import USD, make_currency
from hdlib.DateTime.Date import Date

# from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


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
    """
    Set up the parachute forward configuration for a company.
    """
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


def initialize_company(
    company_name: str,
    lower_limit: float = 0.03,
    floating_pnl_fraction: float = 0.0
):
    from main.apps.account.models import Company, Account
    from main.apps.account.models.parachute_data import ParachuteData
    from main.apps.hedge.models import HedgeSettings

    company = Company.create_company(company_name, currency=USD)

    account = Account.get_or_create_account(name="High",
                                            company=company,
                                            account_type=Account.AccountType.DEMO)
    logger.debug(f"Account {account} has id {account.id}")
    # Set up the account as a parachute account.
    account.strategy = Account.AccountStrategy.PARACHUTE
    account.save()

    # ==========================================================================================================
    # Set parachute forward configuration.
    # ==========================================================================================================

    setup_company_parachute_forward_config(company=company)

    # ==========================================================================================================
    # Create the parachute configuration
    # ==========================================================================================================

    # Delete any preexisting parachute data for the account.
    ParachuteData.objects.filter(account=account).delete()
    ParachuteData.create_for_account(account, lower_p=0.97, upper_p=0.99, lower_limit=lower_limit,
                                     floating_pnl_fraction=floating_pnl_fraction)
    logger.debug(f"Set the lower value for the account to be {lower_limit}.")

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
    return company, account


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


def select_dates_for_scenarios(num_samples: int, first_start_date: Date, last_start_date: Date):
    """
    This function determines how to choose what dates scenarios should begin on.
    """
    scenario_dates = []

    # Generate the start dates. Make sure none of the start dates are on weekends.
    # NOTE(Nate): Technically, we should also check for holidays, but if we stride though days by enough, it is unlikely
    # that two days would roll to the same business date.
    num_potential_start_dates = Date.days_between(first_start_date, last_start_date)
    start_dates = [date for date in [first_start_date + i for i in range(0, num_potential_start_dates)] if
                   date.day_of_week() not in {6, 7}]

    if len(start_dates) < num_samples:
        logger.warning(f"We only have {len(start_dates)} potential start dates, "
                       f"but {num_samples} samples were requested.")

    # Calculate what stride we need.
    stride = len(start_dates) // num_samples
    logger.debug(f"Calculated stride to be {stride}.")

    num_simulations_run = 0
    for count, start_date in enumerate(start_dates):
        if count % stride != 0:
            continue
        scenario_dates.append(start_date)

        num_simulations_run += 1
        if num_samples <= num_simulations_run:
            logger.debug(
                f"We have run {num_simulations_run} simulations. This is the requested number of samples. Exiting.")
            break

    return scenario_dates


def initialize_account_for_parachute(
    account,
    start_date: Date,
    currency: str = 'EUR',
    amount: float = -1000000,
    periodicity: Optional[str] = None,
    final_expiry_days: int = 365
):
    from main.apps.account.models import CashFlow

    def create_chunk(expiry: Date):
        CashFlow.create_cashflow(account=account, date=start_date if periodicity else expiry,
                                 currency=make_currency(currency), amount=amount,
                                 roll_convention=CashFlow.RollConvention.NEAREST,
                                 status=CashFlow.CashflowStatus.ACTIVE,
                                 periodicity=periodicity,
                                 end_date=expiry if periodicity else None)

    create_chunk(start_date + final_expiry_days)

    logger.debug("Created settings for account")
    logger.debug("\n")

    return account


def extract_statistics(
    company_name,
    account,
    start_date: Date,
    end_date: Date,
    data: dict,
    paths: dict,
    index: int,
    currency: str,
    amount: float,
    lower_limit: float = 0.03,
    floating_pnl_fraction: float = 0.0
):
    from main.apps.hedge.models import ParachuteRecordAccount

    bucketed_parachute_records = ParachuteRecordAccount.get_in_range_bucketed(account=account)

    aggregate_buckets = True  # Set to true to use new approach that aggregates buckets. False tests with old version,
    # In case of a single bucket, the two approaches should match

    def add_static_fields(records):
        data.setdefault("CompanyName", []).append(company_name)
        data.setdefault("Currency", []).append(currency)
        data.setdefault("Amount", []).append(amount)
        data.setdefault("LowerLimit", []).append(lower_limit)
        data.setdefault("FloatingPnlFraction", []).append(floating_pnl_fraction)
        data.setdefault("StartDate", []).append(start_date)
        data.setdefault("EndDate", []).append(end_date)
        data.setdefault("NumRecords", []).append(len(records))

    def add_paths(records):
        paths[f"Days_{index}"] = [Date.days_between(start_date, x.time) for x in records]
        paths[f"CompleteAccountValue_{index}"] = [x.complete_bucket_value for x in records]
        paths[f"UnhedgedValue_{index}"] = [x.cashflows_npv for x in records]
        paths[f"AccountValue_{index}"] = [x.bucket_value for x in records]

    if len(bucketed_parachute_records) > 1 and aggregate_buckets:

        initial_account_val, complete_bucket_val, bucket_val, bucket_npv, uhedged_npv = 0, 0, 0, 0, 0
        forwards_pnl, sum_abs_remaining, terminal_diff_from_limit = 0, 0, 0

        # Initialize path values
        fist_key = list(bucketed_parachute_records.keys())[0]
        parachute_records = bucketed_parachute_records[fist_key]

        add_static_fields(parachute_records)
        add_paths(parachute_records)  # initialize them here, we will then update in loop through records

        for key, parachute_records in bucketed_parachute_records.items():
            if len(parachute_records) == 0:
                logger.warning(f"No parachute records found for bucket {key}.")
                continue

            first_record = parachute_records[0]
            last_record = parachute_records[-1]
            terminal_diff_from_limit += last_record.complete_bucket_value - last_record.adjusted_limit_value

            initial_account_val += first_record.bucket_value
            complete_bucket_val += last_record.complete_bucket_value
            bucket_val += last_record.bucket_value
            uhedged_npv += last_record.cashflows_npv
            bucket_npv += last_record.bucket_npv
            forwards_pnl += last_record.forwards_pnl
            sum_abs_remaining += last_record.sum_abs_remaining

            if key != fist_key:
                for i in range(len(parachute_records)):
                    record = parachute_records[i]
                    paths[f"CompleteAccountValue_{index}"][i] += record.complete_bucket_value
                    paths[f"UnhedgedValue_{index}"][i] += record.cashflows_npv
                    paths[f"AccountValue_{index}"][i] += record.bucket_value

        # Aggregate the records across buckets
        data.setdefault("InitialAccountValue", []).append(initial_account_val)
        data.setdefault("TerminalDiffFromLimit", []).append(terminal_diff_from_limit)
        data.setdefault("CompleteBucketValue", []).append(complete_bucket_val)
        data.setdefault("BucketValue", []).append(bucket_val)
        data.setdefault("UnhedgedNPV", []).append(uhedged_npv)
        data.setdefault("BucketNPV", []).append(bucket_npv)
        data.setdefault("ForwardsPnL", []).append(forwards_pnl)
        data.setdefault("SumAbsRemaining", []).append(sum_abs_remaining)

        # Values that dont make sense when aggregating
        # data.setdefault("LimitValue", []).append(dummy_val)
        # data.setdefault("AdjustedLimitValue", []).append(dummy_val)
        # data.setdefault("MaxPnL", []).append(dummy_val)
        # data.setdefault("ImpliedMinimumClientCash", []).append(dummy_val)
        # data.setdefault("ClientImpliedCashPnL", []).append(dummy_val)

    else:
        for key, parachute_records in bucketed_parachute_records.items():
            if len(parachute_records) == 0:
                logger.warning(f"No parachute records found for bucket {key}.")

            first_record = parachute_records[0]
            last_record = parachute_records[-1]

            terminal_diff_from_limit = last_record.complete_bucket_value - last_record.adjusted_limit_value

            # Initialize data with static fields
            add_static_fields(parachute_records)

            # Add in the dynamic fields
            data.setdefault("InitialAccountValue", []).append(first_record.bucket_value)
            data.setdefault("CompleteBucketValue", []).append(last_record.complete_bucket_value)
            data.setdefault("BucketValue", []).append(last_record.bucket_value)
            data.setdefault("UnhedgedNPV", []).append(last_record.cashflows_npv)
            data.setdefault("LimitValue", []).append(last_record.limit_value)
            data.setdefault("AdjustedLimitValue", []).append(last_record.adjusted_limit_value)
            data.setdefault("BucketNPV", []).append(last_record.bucket_npv)
            data.setdefault("ForwardsPnL", []).append(last_record.forwards_pnl)
            data.setdefault("SumAbsRemaining", []).append(last_record.sum_abs_remaining)
            data.setdefault("MaxPnL", []).append(last_record.max_pnl)
            data.setdefault("ImpliedMinimumClientCash", []).append(last_record.implied_minimum_client_cash)
            data.setdefault("ClientImpliedCashPnL", []).append(last_record.client_implied_cash_pnl)
            data.setdefault("TerminalDiffFromLimit", []).append(terminal_diff_from_limit)
            # data.setdefault("NumRecords", []).append(len(parachute_records))

            # Fill in paths data
            add_paths(parachute_records)

            # There should be no more buckets, but just to be clear, this is only set up to handle one bucket.
            break


def run(
    num_samples: int,
    time_horizon_days: int,
    data_path: str,
    company_to_run: str = "ParachuteTesting",
    currency: str = 'EUR',
    amount: float = -1000000,
    lower_limit: float = 0.03,
    floating_pnl_fraction: float = 0.0,
    periodicity: Optional[str] = None
):
    min_start_date = Date.create(year=2012, month=1, day=1, hour=23)

    # NOTE(Nate): Picked arbitrarily. We should pick this as the first (or one of the first) days on which we have data.
    first_start_date = min_start_date + timedelta(days=random.randint(1, 3650), minutes=random.randint(1, 60 * 24))

    # TODO: Set this to be the last day on which we have data minus time_horizon_days, so we have the maximum amount of
    #  data to work with.
    last_start_date = Date.create(year=2023, month=1, day=1, hour=23)

    logger.debug(f"Our backtesting company is named '{company_to_run}'.")
    logger.debug(f"Our region of available days for testing is between {first_start_date} and {last_start_date}.")

    # Set up a company and the account to run as a parachute account, if it does not exist.
    logger.debug(f"Initializing company {company_to_run} for backtest.")

    clean_hedging_related(company_to_run)
    company, account = initialize_company(
        company_name=company_to_run,
        lower_limit=lower_limit,
        floating_pnl_fraction=floating_pnl_fraction,
    )

    logger.debug(f"Creating start dates for scenarios.")
    scenario_dates = select_dates_for_scenarios(num_samples=num_samples, first_start_date=first_start_date,
                                                last_start_date=last_start_date)

    # The backtest fills in this collection of data.
    data, paths = {}, {}

    for num_simulations_run, start_date in enumerate(scenario_dates):
        end_date = start_date + time_horizon_days
        logger.debug(f"Running simulation {num_simulations_run + 1} of {num_samples}. "
                    f"Start date is {start_date}, end date is {end_date}.")

        logger.debug(f"Cleaning any previous hedge-related data for company {company_to_run}.")
        clean_hedging_related(company_to_run)
        logger.debug(f"Done cleaning up company {company_to_run}.")

        # Set up the company for the backtest.
        initialize_account_for_parachute(
            account=account,
            start_date=start_date,
            currency=currency,
            amount=amount,
            periodicity=periodicity
        )

        # Run the backtest
        try:
            run_for_company(company=company, start_date=start_date, end_date=end_date)
            logger.debug(f"Done running simulation for company {company_to_run}, scenario {num_simulations_run}.")
            exited_successfully = True
        except Exception as ex:
            logger.error(f"Exception occurred during the run of simulation {num_simulations_run}: {ex}")
            exited_successfully = False

        # Extract all statistics we want to keep.
        extract_statistics(
            company_name=company_to_run,
            data=data,
            paths=paths,
            account=account,
            start_date=start_date,
            end_date=end_date,
            index=num_simulations_run,
            currency=currency,
            amount=amount,
            lower_limit=lower_limit,
            floating_pnl_fraction=floating_pnl_fraction,
        )
        data.setdefault("ExitedSuccessfully", []).append(exited_successfully)

    logger.debug(f"Done running scenarios, writing data to directory.")

    try:
        os.makedirs(data_path + "/statistics", exist_ok=True)
        stats = pd.DataFrame(data)
        stats.to_csv(f"{data_path}/statistics/{company_to_run}__statistics.csv", index=False)
    except Exception as ex:
        logger.error(f"Error storing statistics to file: {ex}")
        logger.debug(f"Dumping statistics map:\ndata={data}")

    # Need to make sure all the paths are the same length.
    max_length = np.max([len(path) for _, path in paths.items()])
    logger.debug(f"Padding data to length {max_length}.")
    # Append NaNs to the end of each path to make them all the same length.
    for key, path in paths.items():
        paths[key] = path + [np.nan] * (max_length - len(path))
    try:
        os.makedirs(data_path + "/paths", exist_ok=True)
        path_df = pd.DataFrame(paths)
        path_df.to_csv(f"{data_path}/paths/{company_to_run}__paths.csv", index=False)
    except Exception as ex:
        logger.error(f"Error storing paths to file: {ex}")
        logger.debug(f"Dumping paths map:\npaths={paths}")


def run_for_company(company, start_date: Date, end_date: Date):
    from main.apps.hedge.services.eod_and_intra import EodAndIntraService
    from main.apps.hedge.models import CompanyHedgeAction

    date = start_date
    it = 1
    while date <= end_date:
        # TODO: Check for holidays other than weekends?
        while date.day_of_week() in {6, 7}:
            date += 1

        if end_date < date:
            break

        logger.debug(f"Starting simulation of day {date} (day {it}).")

        start_time = Date.now()

        logger.debug(f"Starting EOD flow for {company} at simulated time {date}")
        status = EodAndIntraService(date).start_eod_flow_for_company(time=date, company=company)
        logger.debug(f"Done starting EOD flow for {company}, status: {status}")
        if not status.is_error():
            logger.debug(f"Ending EOD flow for {company}")

            company_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company)
            logger.debug(f"Last company hedge action was id = {company_hedge_action.id}.")

            # Some time went by waiting for the orders to fill.
            ready_for_end_time = Date.now()
            diff = ready_for_end_time - start_time
            date_end_time = date + diff

            logger.debug(f"Ending EOD flow for {company} at simulated time {date_end_time}")
            status = EodAndIntraService(date_end_time).end_eod_flow_for_company(time=date_end_time, company=company)
            logger.debug(f"Ended EOD flow for company. Status was: {status}")

        else:
            logger.error(f"Status was error from starting EOD flow: {status}")

        logger.debug(f"Ending simulation of day {date}.\n\n")
        # Go to the next date.
        date += 1
        it += 1

    logger.debug("Done with RUNNING.")


def django_setup():
    # If the connected DB is the remote (real) server, do not allow the program to run.
    # only_allow_local()

    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()


if __name__ == '__main__':
    django_setup()
    logger.debug(f"Done setting up django. Starting backtest.")

    # Set num_samples to the first command-line argument if provided, otherwise default to 10
    num_samples_ = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    # Set time_horizon_days to the second command-line argument if provided, otherwise default to 30
    time_horizon_days_ = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # Set data_path to the third command-line argument if provided, otherwise default to the current working directory
    data_path_ = str(sys.argv[3]) if len(sys.argv) > 3 else os.getcwd()

    # Set company_to_run
    company_to_run_ = str(sys.argv[4]) if len(sys.argv) > 4 else "ParachuteTesting"

    # Set currency
    currency_ = str(sys.argv[5]) if len(sys.argv) > 5 else "EUR"

    # Set amount
    amount_ = float(sys.argv[6]) if len(sys.argv) > 6 else -1000000

    # Set lower_limit
    lower_limit_ = float(sys.argv[7]) if len(sys.argv) > 7 else 0.01

    # Set floating_pnl_fraction
    floating_pnl_fraction_ = float(sys.argv[8]) if len(sys.argv) > 8 else 0.0

    # Set periodicity (e.g. "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE")
    periodicity_ = str(sys.argv[9]) if len(sys.argv) > 9 else None

    try:
        os.makedirs(data_path_, exist_ok=True)
        logger.debug(f"\n"
                    f"num_samples={num_samples_} \n"
                    f"time_horizon_days={time_horizon_days_} \n"
                    f"data_path={data_path_} \n"
                    f"company_to_run={company_to_run_} \n"
                    f"currency={currency_} \n"
                    f"amount={amount_} \n"
                    f"lower_limit={lower_limit_} \n"
                    f"floating_pnl_fraction={floating_pnl_fraction_} \n"
                    f"periodicity={periodicity_} \n"
                    )
        run(
            num_samples=num_samples_,
            time_horizon_days=time_horizon_days_,
            data_path=data_path_,
            company_to_run=company_to_run_,
            currency=currency_,
            amount=amount_,
            lower_limit=lower_limit_,
            floating_pnl_fraction=floating_pnl_fraction_,
            periodicity=periodicity_
        )
    except Exception as ex:
        logger.fatal(f"Unhandled exception occurred while running parachute test: {ex}")
        exit(1)
    logger.debug(f"Done with all backtest. Exiting. It has been a pleasure working with you.")
