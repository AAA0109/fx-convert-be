from typing import Optional

import numpy as np
from matplotlib import pyplot as plt

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date

logger = get_logger(level=logging.INFO)


def sort_pair(lists):
    for lst in lists:
        if len(lst) == 0:
            return [[] for _ in lists]
    return zip(*list(sorted(zip(*lists))))


def check_liquidity(company_id):
    from main.apps.hedge.models import AccountDesiredPositions
    from main.apps.hedge.models import LiquidityPoolRecord
    from main.apps.account.services.cashflow_provider import CashFlowProviderService

    account_desired_positions = AccountDesiredPositions.get_desired_positions_for_company(company=company_id)
    liquidity_records = LiquidityPoolRecord.get_records_for_company(company=company_id)

    record_per_cha = {}

    for pos in account_desired_positions:
        record_per_cha.setdefault(pos.company_hedge_action, [[], []])[0].append(pos)
    for record in liquidity_records:
        record_per_cha.setdefault(record.company_hedge_action, [None, []])[1].append(record)

    for hedge_action, data in record_per_cha.items():
        for pos in data[0]:
            exposures = CashFlowProviderService().get_cash_exposures_for_account(
                account=pos.account,
                time=Date.from_datetime(hedge_action.time))

    pass


def check_positions(company_id,
                    image_per_account: bool = False,
                    start_date: Optional[Date] = None,
                    end_date: Optional[Date] = None):
    """
    Check what a company's accounts' positions were, compared to their net exposures.
    """

    from main.apps.hedge.models import FxPosition
    from main.apps.hedge.models import AccountDesiredPositions
    from main.apps.account.services.cashflow_provider import CashFlowProviderService
    from main.apps.currency.models import FxPair
    from main.apps.account.models import Company

    def get_fx(exposure, fxpair: FxPair):
        if fxpair in exposure:
            return exposure.get(fxpair, 0)
        else:
            inverse = FxPair.get_inverse_pair(fxpair)
            return exposure.get(inverse, 0)

    company = Company.get_company(company=company_id)

    # Pull the data from the DB.
    fxpositions_per = FxPosition.get_positions_per_event_per_account(company=company_id,
                                                                     start_date=start_date,
                                                                     end_date=end_date)
    desired_positions = AccountDesiredPositions.get_positions_per_action_per_account(company=company_id,
                                                                                     start_time=start_date,
                                                                                     end_time=end_date
                                                                                     )

    # Get the set of all accounts and all fxpairs referenced by anything.
    accounts = set({})
    fxpairs = set({})
    for event, pos_per_account in fxpositions_per.items():
        for account, fxpositions in pos_per_account.items():
            accounts.add(account)
            for position in fxpositions:
                fxpairs.add(position.fxpair)
    for action, desired_per_action in desired_positions.items():
        for account, desired in desired_per_action.items():
            accounts.add(account)
            for pos in desired:
                fxpairs.add(pos.fxpair)

    transposed_desired = {fxpair: {account: ([], [], []) for account in accounts} for fxpair in fxpairs}
    total_desireds = {fxpair: ([], []) for fxpair in fxpairs}
    total_desireds_pre_liquidity = {fxpair: ([], []) for fxpair in fxpairs}
    for action, desired_per_action in desired_positions.items():
        total_desired = {fxpair: 0 for fxpair in fxpairs}
        total_desired_pre_liquidity = {fxpair: 0 for fxpair in fxpairs}
        for account, desired in desired_per_action.items():
            accounts.add(account)
            for pos in desired:
                pr = transposed_desired[pos.fxpair][account]
                pr[0].append(action.time)
                pr[1].append(pos.amount)
                pr[2].append(pos.amount_pre_liquidity())

                total_desired[pos.fxpair] += pos.amount
                total_desired_pre_liquidity[pos.fxpair] += pos.amount_pre_liquidity()

        for fxpair, total in total_desired.items():
            total_desireds[fxpair][0].append(action.time)
            total_desireds[fxpair][1].append(total)

            total_desireds_pre_liquidity[fxpair][0].append(action.time)
            total_desireds_pre_liquidity[fxpair][1].append(total_desired_pre_liquidity[fxpair])

    # Organize so for each Fx pair, we see the time series of holdings for each account, along with the exposure
    # for each account.
    transposed = {fxpair: {account: ([], [], []) for account in accounts} for fxpair in fxpairs}
    total_exposures = {fxpair: ([], []) for fxpair in fxpairs}
    total_holdings = {fxpair: ([], []) for fxpair in fxpairs}
    for event, pos_per_account in sorted(fxpositions_per.items(), key=lambda x: x[0].time):
        total_exposure = {fxpair: 0 for fxpair in fxpairs}
        total_holding = {fxpair: 0 for fxpair in fxpairs}
        for account, fxpositions in pos_per_account.items():

            exposures = CashFlowProviderService().get_cash_exposures_for_account(
                account=account,
                time=Date.from_datetime(event.time)).net_exposures()

            for position in fxpositions:
                pr = transposed[position.fxpair][account]
                exp = get_fx(exposures, position.fxpair)

                pr[0].append(event.time)
                pr[1].append(position.amount)
                pr[2].append(exp)

                total_exposure[position.fxpair] += exp
                total_holding[position.fxpair] += position.amount

        for fxpair, total in total_exposure.items():
            total_exposures[fxpair][0].append(event.time)
            total_exposures[fxpair][1].append(total)

            total_holdings[fxpair][0].append(event.time)
            total_holdings[fxpair][1].append(total_holding[fxpair])

    # Make a plot for each Fx pair.
    for fxpair, positions_per_account in transposed.items():
        if not image_per_account:
            fig = plt.figure(figsize=(15, 15))

            # Plot total exposure.
            times, exposures = sort_pair(total_exposures[fxpair])
            plt.plot(times, exposures, color="black", linestyle=":", label=f"Total exposure in {fxpair}")
            # Plot total holding
            times, holding = sort_pair(total_holdings[fxpair])
            plt.plot(times, holding, color="gray", linestyle="--", label=f"Total company holding of {fxpair}")

            times, desired = sort_pair(total_desireds_pre_liquidity[fxpair])
            plt.plot(times, desired, color="blue", linestyle="-", label=f"Total desired {fxpair}, pre-liquidity")

            # Since the net liquidity adjusted desired positions must be the same as the original desired positions,
            # I am not plotting them separately.

        desired_for_fx = transposed_desired[fxpair]

        i = 0
        for account, (t, amounts, exposure) in sorted(positions_per_account.items()):
            if image_per_account:
                fig = plt.figure(figsize=(15, 15))

                # Plot total exposure.
                times, exposures = sort_pair(total_exposures[fxpair])
                plt.plot(times, exposures, color="black", linestyle=":", label=f"Total exposure in {fxpair}")
                # Plot total holding
                times, holding = sort_pair(total_holdings[fxpair])
                plt.plot(times, holding, color="gray", linestyle="--", label=f"Total company holding of {fxpair}")

                times, desired = sort_pair(total_desireds_pre_liquidity[fxpair])
                plt.plot(times, desired, color="blue", linestyle="-", label=f"Total desired {fxpair}")

                # Since the net liquidity adjusted desired positions must be the same as the original desired positions,
                # I am not plotting them separately.

            t, amounts = sort_pair((t, amounts))
            if len(t) != 0:
                plt.plot(t, amounts, label=f"Amount of {fxpair} for '{account}' ({account.id})",
                         color=f"C{i}")
                plt.plot(t, exposure, label=f"Exposure to {fxpair} for '{account}' ({account.id})",
                         color=f"C{i}", linestyle="--")

            t, desired, desired_pre_liquidity = sort_pair(desired_for_fx[account])
            if len(t) != 0:
                plt.plot(t, desired, label=f"Liquidity adjusted {fxpair} desired by '{account}' ({account.id})",
                         color=f"C{i}",
                         linestyle="-.",
                         marker="x")
                plt.scatter(t, desired_pre_liquidity,
                            label=f"Amount of {fxpair} desired by '{account}' ({account.id})", color=f"C{i}",
                            marker="o", linestyle="-", s=10)
            i += 1

            if image_per_account:
                plt.xlabel(f"Date")
                plt.ylabel(f"Amount")
                plt.title(f"Holdings of {fxpair} for '{company}' (id={company_id})")
                plt.legend()
                plt.show()

                plt.close(fig)

        # plt.plot([Date.from_int(2023_03_23), Date.from_int(2023_03_23)], [-250_000, 500_000], color="black")
        # plt.plot([Date.from_int(2023_03_24), Date.from_int(2023_03_24)], [-250_000, 500_000], color="black")

        if not image_per_account:
            plt.xlabel(f"Date")
            plt.ylabel(f"Amount")
            plt.title(f"Holdings of {fxpair} for '{company}' (id={company_id})")
            plt.legend()
            plt.show()

            plt.close(fig)


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    check_positions(company_id=18)
    # check_positions(company_id=23)  # , image_per_account=True)
