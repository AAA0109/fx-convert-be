import numpy as np
from matplotlib import pyplot as plt

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


def track_company(company_id):
    from main.apps.hedge.models import FxPosition
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.account.models import Company

    company = Company.get_company(company_id)
    positions = FxPosition.objects.filter(company_event__company_id=company_id)
    positions_by_event = {}
    all_fx = set({})
    for pos in positions:
        positions_by_event.setdefault(pos.company_event, []).append(pos)
        all_fx.add(pos.fxpair)
    positions_by_event = dict(sorted(positions_by_event.items(), key=lambda x: x[0].time))

    fx_provider = FxSpotProvider()

    times = []
    amounts = {fx: [] for fx in all_fx}
    pos_values = {fx: [] for fx in all_fx}
    for event, positions in positions_by_event.items():
        times.append(event.time)
        spot_cache = fx_provider.get_spot_cache(time=event.time)

        for fx in all_fx:
            amounts[fx].append(0.)
            pos_values[fx].append(0.)
        for pos in positions:
            amounts[pos.fxpair][-1] = pos.amount
            pos_values[pos.fxpair][-1] = spot_cache.position_value(pos, company.currency)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 9))
    fig.suptitle('Company FxPair holding and prices')

    for fx, values in amounts.items():
        ax1.plot(times, values, label=f"{fx}", marker="x")

    for fx, values in pos_values.items():
        ax2.plot(times, values, label=f"{fx}", marker="x")

    ax1.set_ylabel("Amount of FxPair held")
    ax1.set_xlabel("Reference date")
    ax1.legend()

    ax2.set_ylabel("Value of FxPair held")
    ax2.set_xlabel("Reference date")
    ax2.legend()

    fig.autofmt_xdate()
    fig.show()


def track_account(account_id):
    from main.apps.account.models import Account
    from main.apps.hedge.models import FxPosition
    from main.apps.hedge.models import AccountDesiredPositions

    account = Account.get_account(account_id)

    fxpositions = FxPosition.objects.filter(account_id=account_id)
    desired = AccountDesiredPositions.objects.filter(account_id=account_id)

    all_fx, all_times = set({}), set({})
    positions_by_time, desired_by_time = {}, {}
    for position in fxpositions:
        all_fx.add(position.fxpair)
        positions_by_time.setdefault(position.company_event.time, {})[position.fxpair] = position

    for position in desired:
        all_fx.add(position.fxpair)
        desired_by_time.setdefault(position.company_hedge_action.time, {})[position.fxpair] = position

    for fx in all_fx:
        t1, t2, actual, desired_pos = [], [], [], []
        for time, positions in positions_by_time.items():
            t1.append(time)
            pos = positions.get(fx, None)
            actual.append(pos.amount if pos else 0.)

        for time, desireds in desired_by_time.items():
            t2.append(time)
            des = desireds.get(fx, None)
            desired_pos.append(des.amount if des else 0.)

        if len(t2) == 0 and len(t1) == 0:
            continue
        min_t = t1[0] if 0 == len(t2) else t2[0] if len(t1) == 0 else min(t1[0], t2[0])
        max_t = t1[-1] if 0 == len(t2) else t2[-1] if len(t1) == 0 else max(t1[-1], t2[-1])

        if np.min(desired_pos) != 0 or np.max(desired_pos) != 0 or np.min(actual) != 0 or np.max(actual) != 0:
            fig = plt.figure(figsize=(12, 8))
            plt.plot([min_t, max_t], [0., 0.], linestyle="--", color="black")
            plt.step(t1, actual, label=f"Actual position of {fx}", marker="x", where="post")
            plt.step(t2, desired_pos, label=f"Desired position of {fx}", marker="x", where="post")
            plt.title(f"Positions for {fx} for account {account}")
            plt.legend()
            fig.autofmt_xdate()
            plt.show()
        else:
            logger.debug(f"All positions and desired positions were zero for account {fx}, account {account}")


def track_accounts_of_company(company_id):
    from main.apps.account.models import Account
    accounts = Account.get_account_objs(company=company_id)
    for account in accounts:
        track_account(account.id)


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    track_company(company_id=16)
    track_accounts_of_company(company_id=16)
