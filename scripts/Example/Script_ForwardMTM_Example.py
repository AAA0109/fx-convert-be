import os, sys

# from scripts.lib.only_local import only_allow_local


"""
Example Script for marking to market a cashflow using forwards
"""


def run():
    from main.apps.marketdata.models import IrCurve
    from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider, FxForwardProvider
    from main.apps.marketdata.services.fx.fx_provider import ForwardImpliedDiscountCurve
    from hdlib.DateTime.Date import Date
    from hdlib.AppUtils.log_util import get_logger, logging

    import matplotlib.pyplot as plt
    import numpy as np

    logger = get_logger(level=logging.INFO)

    # NOTE: the ref_date is the "pricing date"
    ref_date = Date.from_int(20240307)  # just for example, in general dont pass a date for live hedge

    spot_provider = FxSpotProvider()
    fwd_provider = FxForwardProvider(fx_spot_provider=spot_provider)

    # User Details
    domestic = "USD"

    # Cashflow Details
    currency = "EUR"
    amount = 1
    dtm = 31
    spot_rate = 1.0948
    value_date = ref_date + dtm

    # Get the fwd (projection) Curve
    fx_pair = f"{currency}/{domestic}"

    tenors = ['SN','1W','2W','3W','1M','2M','3M','4M','5M','6M','9M','1Y']
    curve = fwd_provider.get_forward_bid_ask_curve(pair=fx_pair, date=ref_date, tenors=tenors, spot=spot_rate)

    """
    =================
    # Example -1:
    =================
    Get an implied discount curve.  Assume we want discounts for currency XXX where whe have forwards and
    discounts for YYY.  So we forward curve for XXX/YYY, and imply XXX discounts from that
    """
    # Get the discount curve for quote
    pair_0 = f"INR/USD"

    ois_curve_id = IrCurve.get_ois_curve_id_for_currency(currency='USD')
    quote_depo = MdIrProviderService.get_discount_curve(ir_curve=ois_curve_id, date=ref_date)

    spot_0 = spot_provider.get_spot_value(fx_pair=pair_0, date=ref_date)
    curve_0 = fwd_provider.get_forward_bid_ask_curve(pair=pair_0, date=ref_date, tenors=tenors, spot=spot_0)

    # Imply the discount curve for base currency
    base_depo = ForwardImpliedDiscountCurve(forward_curve=curve_0, quote_depo=quote_depo)

    pillars = np.asarray([0, 0.05, 0.1, 0.125, 0.25, 0.4, 0.5, 0.75, 1.0, 2.0, 3.0])
    discs = base_depo.at_T(pillars)
    plt.plot(pillars, discs)
    plt.show()


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

    print(f"\nExample 0: Inputs: cf amount = {amount}, dtm = {dtm}, pair = {fx_pair}\n"
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
    yield_in = 0.016904322115318983
    solved_points, solved_rate = curve.solve_points_and_fwd_from_yield_at_D(date=value_date, spot=spot_in,
                                                                            annual_yield=yield_in)

    print(f"\nExample 2: Inputs:  spot = {spot_in}, yield = {yield_in} (ann), dtm = {dtm}\n"
          f"           Outputs: fwd points = {solved_points}, fwd rate = {solved_rate}\n")

    """
    =================
    # Example 3:
    =================
    Forward Price: PROVIDED
    Value Date: PROVIDED
    Returns: Spot price
    """
    fwd_in = 1.096169
    solved_spot = curve.solve_spot_from_fwd_at_D(date=value_date, fwd=fwd_in)

    print(f"\nExample 3: Inputs: fwd = {fwd_in},  dtm = {dtm}\n"
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
    fwd_in = 1.096169
    spot_in = spot_rate

    # Case I: solve the forward points
    solved_points = curve.solve_points(spot=spot_in, fwd=fwd_in)

    # Case II: solve the annualized (simple) yield
    solved_ann_yield = curve.solve_points_yield_at_D(date=value_date, spot=spot_in, fwd=fwd_in, annualized=True)

    # Case III: solve the daily (simple) yield
    solved_daily_yield = curve.solve_points_yield_at_D(date=value_date, spot=spot_in, fwd=fwd_in, annualized=False)

    print(f"\nExample 4: Inputs: fwd = {fwd_in}, spot = {spot_in},  dtm = {dtm}\n"
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
