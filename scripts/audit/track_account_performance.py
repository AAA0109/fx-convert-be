import numpy as np
from matplotlib import pyplot as plt

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date

logger = get_logger(level=logging.INFO)


def fill_in():
    from main.apps.history.models import AccountSnapshot
    for snapshot in AccountSnapshot.objects.all():
        if 0 < snapshot.daily_unhedged_variance:
            snapshot.one_day_variance_ratio = snapshot.daily_hedged_variance / snapshot.daily_unhedged_variance
        else:
            snapshot.one_day_variance_ratio = None
        snapshot.save()


def run():
    from main.apps.auditing.services.auditing import AuditingService

    AuditingService.account_value_change_explained_snapshots(ending_snapshot=3430)

    AuditingService.changes_explained_for_snapshot(3430)


def track_all_account_performances():
    from main.apps.account.models import Account

    for account in Account.objects.all():
        track_account_performance(account.pk)


def check_snapshot_by_id(snapshot_id: int):
    from main.apps.history.models import AccountSnapshot
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency
    from main.apps.account.models import Broker
    from main.apps.hedge.services.cost import CostProviderService
    from main.apps.history.services.snapshot import SnapshotCreatorService

    snapshot = AccountSnapshot.objects.get(pk=snapshot_id)
    time = Date.from_datetime(snapshot.snapshot_time)
    account = snapshot.account

    # FxSpotProvider().get_spot_cache(time=snapshot.snapshot_time)
    universe_provider_service = UniverseProviderService()

    usd = Currency.get_currency("USD")
    universe = universe_provider_service.make_cntr_currency_universe(
        domestic=usd, ref_date=time, bypass_errors=True)

    # FUTURE IMPROVEMENT: just get the broker for the account
    brokers = Broker.objects.all()
    rates_caches = CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
    snapshot_creator = SnapshotCreatorService(universes={usd: universe}, rates_caches=rates_caches)
    return snapshot_creator.generate_snapshot(account=account)


def find_bad_days(account, times, hedged_var, unhedged_var):
    from main.apps.history.models import AccountSnapshot
    from main.apps.hedge.models import CompanyHedgeAction
    from main.apps.auditing.services.auditing import AuditingService

    where = np.where(hedged_var > unhedged_var)

    bad_times = times[where]
    ratios = hedged_var[where] / unhedged_var[where]

    for t, r in zip(bad_times, ratios):
        # Find snapshot.
        snapshots = AccountSnapshot.get_snapshots(account=account, start_time=t, end_time=t)
        if snapshots:
            for snapshot in snapshots:  # Should just be 1.
                print(f"On {t} ratio was {r}")
                print(f"  * Snapshot {snapshot.id}")

            # Get the company hedge action.
            action = CompanyHedgeAction.get_latest_company_hedge_action(company=account.company,
                                                                        time=t,
                                                                        inclusive=True)
            try:
                AuditingService.changes_explained(ending_company_hedge_action=action)
            except Exception:
                pass
        else:
            print(f"On {t} ratio was {r}")


def plot_account_pnl(account_id):
    """
    Plot the spot and forward PnL for an account.
    """
    from main.apps.account.models import Account
    from main.apps.history.services.snapshot_provider import SnapshotProvider

    account = Account.get_account(account_id)
    times, spot_pnl, forward_pnl = SnapshotProvider().get_account_unrealized_pnls_ts(account=account)

    plt.figure(figsize=(12, 8))
    plt.plot(times, spot_pnl, label="Spot PnL")
    plt.plot(times, forward_pnl, label="Forward PnL")
    plt.xlabel("Date")
    plt.ylabel("PnL")
    plt.title(f"PnL for account {account} (id={account_id})")
    plt.legend()
    plt.show()


def plot_account_values(account_id):
    from main.apps.account.models import Account
    from main.apps.history.services.snapshot_provider import SnapshotProvider
    from main.apps.hedge.models import HedgeSettings

    account = Account.get_account(account_id)
    time, hedged_value = SnapshotProvider().get_account_hedged_value_ts(account=account)
    time, unhedged_value = SnapshotProvider().get_account_unhedged_value_ts(account=account)

    plt.figure(figsize=(12, 8))
    plt.plot(time, hedged_value, label="Hedged value")
    plt.plot(time, unhedged_value, label="Unhedged value")
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.title(f"Values for account {account} (id={account_id})")
    plt.legend()
    plt.show()


def track_account_performance(account_id):
    from main.apps.account.models import Account
    from main.apps.history.services.snapshot_provider import SnapshotProvider
    from main.apps.hedge.models import HedgeSettings

    account = Account.get_account(account_id)
    time, hedged_var, unhedged_var = SnapshotProvider.get_daily_variances_ts(account=account)

    if len(time) == 0:
        logger.debug(f"No data for account {account}, not plotting anything.")
        return

    do_daily_var_plot = False

    if do_daily_var_plot:
        fig = plt.figure(figsize=(12, 8))
        plt.plot(time, hedged_var, label="Hedged var production")
        plt.plot(time, unhedged_var, label="Unhedged var production")

        plt.legend()
        plt.yscale("log")
        plt.xlabel("Date")
        plt.ylabel("Daily Variance 'production' (log-scale)")
        plt.title(f"Performance for account {account} (id={account_id})")
        plt.show()

        plt.close(fig)

    periods = [3, 5, 15]

    fig, axs = plt.subplots(len(periods), sharex=True, figsize=(12, 8))
    fig.suptitle('Vertically stacked subplots')

    hedge_settings = HedgeSettings.get_hedge_account_settings_hdl(account)
    target_vol_reduction = hedge_settings.custom_settings.get("VolTargetReduction", None)

    reduction_ts = {}
    for it, N in enumerate(periods):
        ave_hedged = np.sqrt(np.convolve(hedged_var, np.ones(N), mode='valid'))
        ave_unhedged = np.sqrt(np.convolve(unhedged_var, np.ones(N), mode='valid'))

        t = time[N - 1:]
        reduction = 1 - ave_hedged / ave_unhedged

        reduction_ts[N] = (t, reduction)

        if len(t) == 0:
            continue

        axs[it].plot(t, reduction, color=f"C{it}")
        axs[it].plot((time[0], time[-1]), (0, 0), linestyle="--", color="black")
        if target_vol_reduction:
            axs[it].plot((time[0], time[-1]), (target_vol_reduction, target_vol_reduction),
                         linestyle="--", color="gray")
        axs[it].set_title(f"Vol reduction ({N}-day average)")

    fig.suptitle(f"Volatility reduction for various periods  for account {account} (id={account_id})")
    plt.show()

    # Find any days where we did worse than expected.
    # find_bad_days(account, time, hedged_var, unhedged_var)


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    # fill_in()
    # run()

    track_account_performance(260)
    track_account_performance(261)
    track_account_performance(262)
