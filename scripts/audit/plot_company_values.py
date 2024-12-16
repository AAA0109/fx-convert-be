from typing import Optional

from hdlib.DateTime.Date import Date
import matplotlib.pyplot as plt


def plot_company_values(company_id):
    from main.apps.history.services.visualization import SnapshotVisualizationService
    from main.apps.account.models import Account
    from main.apps.account.models import CashFlow

    fig = SnapshotVisualizationService().create_accounts_values_figure(company=company_id)
    fig.show()

    # ================================
    # Plot risk reduction
    # ================================

    for account in Account.get_account_objs(company=company_id):
        plot = SnapshotVisualizationService().create_account_allocation_plot(account=account)
        if plot:
            plot.show()


def plot_account_cf_and_positions(company_id):
    from main.apps.account.models import Account
    from main.apps.account.models import CashFlow
    from main.apps.history.services.snapshot_provider import SnapshotProvider
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

    USD = Currency.get_currency("USD")

    p = SnapshotProvider()
    ups = UniverseProviderService()
    spot_provider = FxSpotProvider()

    for account in Account.get_account_objs(company=company_id):
        times, hedged_values, unhedged_values, cashflow_fwds, trading, directional_positions_values \
            = [], [], [], [], [], []

        snapshots = p.get_account_snapshots(account=account)
        for snapshot in snapshots:
            times.append(snapshot.snapshot_time)
            hedged_values.append(snapshot.hedged_value)
            unhedged_values.append(snapshot.unhedged_value)
            cashflow_fwds.append(snapshot.cashflow_fwd)
            directional_positions_values.append(snapshot.directional_positions_value)

            trading.append(snapshot.daily_trading)

        cashflows = CashFlow.objects.filter(account=account).order_by("created")
        cf_additions, cf_amounts = [], []
        spot_cache = None
        for cf in cashflows:
            created = Date.from_datetime(cf.created)
            if 0 < len(cf_additions) and cf_additions[-1].date() < created.date():
                # FX this into USD.
                cf_amounts[-1] += spot_cache.convert_value(value=cf.amount, from_currency=cf.currency, to_currency=USD)
            else:
                cf_additions.append(created)
                cf_amounts.append(cf.amount)
                spot_cache = spot_provider.get_spot_cache(time=created)

        # Create the figure.
        plt.figure(figsize=(12, 8))

        plt.plot((times[0], times[-1]), (0., 0.), linestyle="--", color="gray")
        for t, v in zip(times, trading):
            if v == 0:
                continue
            plt.plot([t, t], [0, v], color="red" if v < 0 else "blue")

        for t, added in zip(cf_additions, cf_amounts):
            plt.plot((t, t), (0, added), color="black")

        plt.plot(times, hedged_values, label="hedged_values")
        plt.plot(times, unhedged_values, label="un-hedged values")
        plt.plot(times, cashflow_fwds, label="cashflow forwards")
        plt.plot(times, directional_positions_values, label="Directional position values")
        plt.xlabel(f"Reference date")
        plt.ylabel(f"Value (USD)")
        plt.title(f"Plot for account {account} (id={account.id})")
        plt.legend()
        plt.show()
        plt.close("all")


def plot_account_positions(account_id: int):
    from main.apps.hedge.models import FxPosition
    from main.apps.history.services.snapshot_provider import SnapshotProvider
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

    ts_per_pair = {}

    USD = Currency.get_currency("USD")
    ups = UniverseProviderService()
    spot_provider = FxSpotProvider()

    positions = FxPosition.get_positions_by_event_and_account(account=account_id)
    last_time: Optional[Date] = None
    for event, pos_by_account in positions.items():
        time = Date.from_datetime(event.time)
        if last_time is None or last_time.date() < time.date():
            spot_cache = spot_provider.get_spot_cache(time=time)

        for account, fxpositions in pos_by_account.items():  # Should only be one account
            for fxposition in fxpositions:
                fxpair = fxposition.fxpair
                amount = fxposition.amount

                data = ts_per_pair.setdefault(fxpair, ([], [], []))
                data[0].append(time)
                data[1].append(amount)
                data[2].append(amount * spot_cache.get_fx(fx_pair=fxpair))

        for pair, ts in ts_per_pair.items():
            if ts[0][-1] != time:
                ts[0].append(time)
                ts[1].append(0.)
                ts[2].append(0.)

    # Get cashflow forwards, for comparison.

    plt.figure(figsize=(12, 8))
    for pair, (times, amounts, usd_amounts) in ts_per_pair.items():
        plt.plot(times, amounts, label=f"Positions for {pair}")
        plt.plot(times, usd_amounts, label=f"Positions for {pair} in USD")

    dates, forwards = SnapshotProvider().get_account_cashflow_fwd_ts(account=account_id)
    plt.plot(dates, forwards, label="Cashflow forwards, USD")

    plt.title(f"Account positions for account 262")
    plt.legend()
    plt.xlabel(f"Reference date")
    plt.ylabel(f"Amount of Fx pair")
    plt.show()


def plot_cashflows(account_id: int):
    from main.apps.account.models import CashFlow

    cashflows = CashFlow.objects.filter(account=account_id).order_by("created")

    value = None

    dates = []
    values = []

    for cf in cashflows:
        if len(dates) == 0 or dates[-1].date() < cf.created.date():
            dates.append(Date.from_datetime(cf.created))
            if value is not None:
                values.append(value)
            value = 0
        # hdl = []
        for c in cf.get_hdl_cashflows():
            if Date.from_int(20240101) < c.pay_date:
                break
            # hdl.append(c)
            value += c.amount
    if value:
        values.append(value)

    plt.figure(figsize=(12, 8))
    plt.scatter(dates, values)
    plt.xlabel(f"Cashflow creation date")
    plt.ylabel(f"Amount")
    plt.title(f"Cashflow additions for account id={account_id}")
    plt.show()


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    plot_company_values(23)
    plot_account_positions(885)
    plot_account_cf_and_positions(company_id=23)
