from hdlib.Universe.Historical.HistUniverseProvider import HistUniverseProvider
from hdlib.Universe.Universe import Universe
from main.apps.currency.models import Currency, FxPair
from main.apps.marketdata.models import FxSpot
from main.apps.marketdata.models.marketdata import DataCut
from main.apps.marketdata.services.data_cut_service import DataCutService


def load_universe(pu: Universe):
    """
    Load all the data from a universe into the database.
    """
    date = pu.ref_date

    # Load all currencies needed by the universe into the database.
    for currency in pu.currencies:
        Currency.create_currency_from_hdl(currency)

    # If there is a data cut for this day (EOD), use that, otherwise create an EOD cut.
    data_cut = DataCutService.get_eod_cut(date=date)
    if data_cut is None:
        status, data_cut = DataCutService.create_cut(date=date, cut_type=DataCut.CutType.EOD)

    # Load all FX assets' spots into the database.
    fx_assets = pu.fx_assets
    all_asset_names = fx_assets.get_all_fx_asset_names()
    for name in all_asset_names:
        asset = fx_assets.get_asset(name)
        fx_pair = asset.fx_pair

        # Create the currencies.
        status, _ = Currency.create_currency(mnemonic=fx_pair.base.get_mnemonic(), name=fx_pair.base.get_name())
        if status.is_error():
            print(f"Error creating currency: {status}")
        status, _ = Currency.create_currency(mnemonic=fx_pair.quote.get_mnemonic(), name=fx_pair.quote.get_name())
        if status.is_error():
            print(f"Error creating currency: {status}")

        # Create the FX asset.
        status, _ = FxPair.create_fxpair(base=fx_pair.base, quote=fx_pair.quote)
        if status.is_error():
            print(f"Error creating fx pair: {status}")

        # Add the spot data.
        status, _ = FxSpot.add_spot(data_cut=data_cut,
                                    pair=fx_pair,
                                    rate=asset.spot)
        if status.is_error():
            print(f"Error adding spot: {status}")

    # for currency in pu.currencies:
    #     ir_asset = pu.get_ir_asset(currency=currency)
    #     if ir_asset is not None and ir_asset.discount_curve is not None:
    #         ir_asset.discount_curve


def load_all_universes(provider: HistUniverseProvider):
    """
    Load all the dates available in a universe provider into the database.
    """
    all_dates = provider.get_all_dates()
    for date in all_dates:
        print(f"Loading universe for date {date}.")
        pu = provider.make_universe(date)
        load_universe(pu)
