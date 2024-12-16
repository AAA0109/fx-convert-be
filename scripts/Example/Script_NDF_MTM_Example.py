import os, sys

# from scripts.lib.only_local import only_allow_local

"""
Example Script for marking to market a cashflow using forwards
"""


def run():
    from main.apps.marketdata.models import IrCurve
    from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService
    from main.apps.marketdata.services.fx.fx_provider import CachedFxSpotProvider, FxForwardProvider
    from main.apps.oems.backend.ccy_utils import determine_rate_side
    from main.apps.oems.backend.calendar_utils import get_fx_settlement_info
    from hdlib.DateTime.Date import Date
    from hdlib.AppUtils.log_util import get_logger, logging

    logger = get_logger(level=logging.INFO)

    # NOTE: the ref_date is the "pricing date"
    ref_date = Date.from_int(20240307)  # just for example, in general dont pass a date for live hedge

    spot_provider = CachedFxSpotProvider()
    fwd_provider = FxForwardProvider(fx_spot_provider=spot_provider)

    # User Details
    from_ccy = "USD"

    # Cashflow Details
    to_ccy = "INR"

    market, side = determine_rate_side( from_ccy, to_ccy  )

    amount = 1
    tenor = '1M'
    spot_rate = 82.785
    fwd_rate = 82.8787
    impl_yield = 0.0133

    info = get_fx_settlement_info( market.market, dt=ref_date, tenor=tenor )
    days = info['days']
    dtm = info['alt_days'] # this isn't the actual number of interest days
    value_date = ref_date + dtm
    tenors = ['SN','1W','2W','3W','1M','2M','3M','4M','5M','6M','9M','1Y'] # will use default

    domestic = market.market[:3]
    foreign  = market.market[3:]
    fx_pair  = f'{domestic}/{foreign}'

    curve = fwd_provider.get_forward_bid_ask_curve(pair=fx_pair, date=ref_date, tenors=tenors, spot=spot_rate)

    """
    =================
    # Example 0:
    =================
    Mark-to-market a cashflow in a foreign currency (ie, compute its net present value in domestic)
    """

    # Get the discount curve
    ois_curve_id = IrCurve.get_ois_curve_id_for_currency(currency=domestic)
    discount = MdIrProviderService.get_discount_curve(ir_curve=ois_curve_id, date=ref_date)

    # Get the Data (all in domestic currency)
    # spot_rate = curve.spot()
    fwd_mid = curve.at_D(date=value_date)
    disc = discount.at_D(date=value_date)

    # Compute the MTM NPV
    npv = amount * fwd_mid * disc

    print(f"\nExample 0: Inputs: cf amount = {amount}, dtm = {days}, pair = {fx_pair}\n"
          f"           Outputs: spot = {spot_rate}, fwd = {fwd_mid}, disc({domestic}) = {disc},"
          f" npv = {npv} ({domestic})\n")

    """
    =================
    # Example 1:
    =================
    Spot Price: PROVIDED
    Value Date: PROVIDED
    Returns: Interpolated forward points and the forward rate.
    """
    fwd_points = curve.points_at_D(value_date)
    fwd_rate = curve.at_D(value_date)

    print(f"Example 1: Inputs: dtm = {dtm}\n"
          f"           Outputs: spot = {curve.spot()} points = {fwd_points}, rate = {fwd_rate}")

    # To get the points and the rate at the same time
    fwd_points, fwd_rate = curve.points_and_fwd_at_D(value_date)

    """
    =================
    # Example 2:
    =================
    Spot Price: PROVIDED
    Value Date: PROVIDED
    Implied Yield (annualized)
    Returns: Forward points and forward rate.
    """
    spot_in = spot_rate
    yield_in = impl_yield
    solved_points, solved_rate = curve.solve_points_and_fwd_from_yield_at_D(date=value_date, spot=spot_in,
                                                                            annual_yield=yield_in)

    print(f"\nExample 2: Inputs:  spot = {spot_in}, yield = {yield_in} (ann), dtm = {days}\n"
          f"           Outputs: fwd points = {solved_points}, fwd rate = {solved_rate}\n")

    """
    =================
    # Example 3:
    =================
    Forward Price: PROVIDED
    Value Date: PROVIDED
    Returns: Spot price
    """
    fwd_in = fwd_rate
    solved_spot = curve.solve_spot_from_fwd_at_D(date=value_date, fwd=fwd_in)

    print(f"\nExample 3: Inputs: fwd = {fwd_in},  dtm = {days}\n"
          f"           Outputs: spot = {solved_spot}")

    """
    =================
    # Example 4:
    =================
    Spot Price: PROVIDED
    Forward Price: PROVIDED
    Returns: Implied Yield (annualized and daily) or Effective Yield (the true yield from spot -> forward)
             or Forward Points.
    """
    fwd_in = fwd_rate
    spot_in = spot_rate

    # Case I: solve the forward points
    solved_points = curve.solve_points(spot=spot_in, fwd=fwd_in)

    # Case II: solve the annualized (simple) yield
    solved_ann_yield = curve.solve_points_yield_at_D(date=value_date, spot=spot_in, fwd=fwd_in, annualized=True)

    # Case III: solve the daily (simple) yield
    solved_daily_yield = curve.solve_points_yield_at_D(date=value_date, spot=spot_in, fwd=fwd_in, annualized=False)

    print(f"\nExample 4: Inputs: fwd = {fwd_in}, spot = {spot_in},  dtm = {days}\n"
          f"           Outputs: points = {solved_points},  "
          f"ann_yield = {solved_ann_yield}, daily_yield = {solved_daily_yield}")

if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    # only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
