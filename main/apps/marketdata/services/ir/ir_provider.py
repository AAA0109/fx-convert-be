from main.apps.currency.models import Currency
from main.apps.marketdata.models.ir.discount import IrDiscount, IrCurve, CurveId
from hdlib.TermStructures.DiscountCurve import DiscountCurve, DiscountCurve_ConstRate, InterpolatedDiscountCurve
from hdlib.DateTime.DayCounter import DayCounter_HD, DayCounter
from hdlib.DateTime.Date import Date

import numpy as np
from typing import Union, Optional, Iterable, Dict, List, Tuple

from main.apps.marketdata.services.data_cut_service import DataCutService, DataCut


class MdIrProviderService(object):
    """
    Market Data Ir Provider class, provides queries and convenience methods for pulling data from the
    database, and mapping it to the internal representations
    """
    day_counter = DayCounter_HD()

    @staticmethod
    def get_discount_curve(ir_curve: Union[CurveId, IrCurve],
                           date: Optional[Date] = None,
                           dc: DayCounter = day_counter,
                           fail_if_missing: bool = False) -> DiscountCurve:
        """
        Get the discount curve for a given curve Id (for a specific currency on given date). If it is not found,
            either return a zero rate discount curve (if fail_if_missing=False), else raise exception
        :param ir_curve: int, the curve pk
        :param date: str, the date
        :param dc: DayCounter, the day counter used to count days along the curve
        :param fail_if_missing: bool, if true, then failure to find the curve results in RuntimeError, rather
            than a 0 rate discount curve
        :return: DiscountCurve, object
        """
        if not Date:
            date = Date.now()

        discounts = IrDiscount.get_discounts_at_time(ir_curves=(ir_curve,), time=date)

        # This curve has no available data on the date, assumes rates are zero
        if len(discounts) == 0:
            if fail_if_missing:
                raise RuntimeError(f"Couldn't retrieve the requested discount curve: {ir_curve}")

            return DiscountCurve_ConstRate(0., ref_date=date, dc=dc)

        ttms = np.ndarray((len(discounts) + 1,))
        dfs = np.ndarray((len(discounts) + 1,))

        ttms[0] = 0.
        dfs[0] = 1.0

        for i in range(len(discounts)):
            forward: IrDiscount = discounts[i]
            df = forward.discount

            ttms[i + 1] = forward.ttm(day_counter=dc)
            if df is not None:
                dfs[i + 1] = forward.discount
            else:
                dfs[i + 1] = dfs[i]

        # Note: no need to sort, b/c they are provided in proper order by Model

        return InterpolatedDiscountCurve.from_log_linear(ttms=ttms, discounts=dfs, ref_date=date, dc=dc)

    @staticmethod
    def get_most_recent_discount_curves(ir_curves: Iterable[Union[IrCurve, CurveId]],
                                        time: Optional[Date] = None,
                                        dc: DayCounter = day_counter,
                                        window: int = 4,
                                        currencies: Optional[Iterable[Currency]] = None,
                                        ) -> Tuple[Dict[CurveId, Optional[InterpolatedDiscountCurve]],
                                                   Dict[CurveId, Optional[Date]]]:
        """
        Get a collection of discount curves using the most recent data available.

        Different from the get_discount_curve function in that it will get the most recent discount curve, only if no
        data can be found within the window will the curve fail to be built.

        This should be more efficient than get_discount_curve since we only execute once for all the discount curves.
        """

        if time is None:
            time = Date.now()
        min_time = time - window

        params = {}
        if currencies:
            params["currency__in"] = currencies
        objects = IrDiscount.objects.filter(curve__in=ir_curves,
                                            data_cut__cut_time__lte=time,
                                            data_cut__cut_time__gte=min_time,
                                            discount__isnull=False,
                                            **params)

        most_recent_dates, discounts = {}, {}
        for discount in objects:
            date = discount.data_time
            curve = discount.curve.id
            if curve not in most_recent_dates or most_recent_dates[curve] < date:
                most_recent_dates[curve] = date
                discounts[curve] = []
            if most_recent_dates[curve] == date:
                discounts[curve].append(discount)

        output, actual_date = {}, {}
        for ir_curve_id in ir_curves:
            ir_curve_id = ir_curve_id.id if isinstance(ir_curve_id, IrCurve) else ir_curve_id
            entries: List[IrDiscount] = discounts.get(ir_curve_id, None)
            if entries is None:
                output[ir_curve_id] = None
                actual_date[ir_curve_id] = None
                continue

            ttms = np.zeros(len(entries) + 1)
            dfs = np.zeros(len(entries) + 1)

            ttms[0] = 0.
            dfs[0] = 1.0

            for it, obj in enumerate(sorted(entries, key=lambda x: x.ttm(day_counter=dc))):
                ttms[it + 1] = obj.ttm(day_counter=dc)
                dfs[it + 1] = obj.discount

            actual_date[ir_curve_id] = Date.from_datetime(most_recent_dates[ir_curve_id])
            output[ir_curve_id] = InterpolatedDiscountCurve.from_log_linear(ttms=ttms,
                                                                            discounts=dfs,
                                                                            ref_date=time,
                                                                            dc=dc)

        return output, actual_date
