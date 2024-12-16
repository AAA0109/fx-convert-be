import unittest

import numpy as np
from django.test import testcases
from hdlib.DateTime.DayCounter import DayCounter_HD

from hdlib.DateTime.Date import Date
from main.apps.currency.models import Currency, FxPair
from main.apps.marketdata.models import IrDiscount, DataCut, IrCurve, BasisConvention, FxSpot, FxForward
from main.apps.marketdata.services.fx.fx_provider import FxForwardProvider
from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService


class HedgePositionServiceTest(testcases.TestCase):
    # noinspection DuplicatedCode
    def test__get_most_recent_forward_curves(self):
        date_1 = Date.create(ymd=2020_01_01, hour=23)
        date_2 = Date.create(ymd=2020_01_02, hour=23)
        date_3 = Date.create(ymd=2020_01_05, hour=23)

        cut_1 = DataCut.create_cut(time=date_1, cut_type=DataCut.CutType.EOD)
        cut_2 = DataCut.create_cut(time=date_2, cut_type=DataCut.CutType.EOD)
        cut_3 = DataCut.create_cut(time=date_3, cut_type=DataCut.CutType.EOD)

        _, USD = Currency.create_currency(mnemonic="USD", name="US Dollars")
        _, EUR = Currency.create_currency(mnemonic="EUR", name="Euros")
        _, HKD = Currency.create_currency(mnemonic="HKD", name="Hong Kong Dollars")

        _, EURUSD = FxPair.create_fxpair(EUR, USD)
        _, USDHKD = FxPair.create_fxpair(USD, HKD)

        # EURUSD: All data.

        FxForward.create_forward_curve(data_cut=cut_1, fx_pair=EURUSD,
                                       tenors=["1W", "2W", "3W"],
                                       fwd_points=[1.00e-2, 2.50e-2, 2.98e-2])
        FxSpot.add_spot(data_cut=cut_1, pair=EURUSD, rate=1.05)

        FxForward.create_forward_curve(data_cut=cut_2, fx_pair=EURUSD,
                                       tenors=["1W", "2W", "3W"],
                                       fwd_points=[1.25e-2, 2.75e-2, 3.02e-2])
        FxSpot.add_spot(data_cut=cut_2, pair=EURUSD, rate=1.07)

        FxForward.create_forward_curve(data_cut=cut_3, fx_pair=EURUSD,
                                       tenors=["1W", "2W", "3W"],
                                       fwd_points=[1.09e-2, 2.70e-2, 1.95e-2])
        FxSpot.add_spot(data_cut=cut_3, pair=EURUSD, rate=1.10)

        # USDHKD: No data on date_2, only spot data on date_3

        FxForward.create_forward_curve(data_cut=cut_1, fx_pair=USDHKD,
                                       tenors=["1W", "2W", "3W"], fwd_points=[2.50e-2, 3.50e-2, 5.4e-2])
        FxSpot.add_spot(data_cut=cut_1, pair=USDHKD, rate=8.00)

        FxSpot.add_spot(data_cut=cut_3, pair=USDHKD, rate=7.92)

        # TESTS

        fwd_curves, actual_dates = FxForwardProvider.get_most_recent_forward_curves(pairs=[EURUSD, USDHKD],
                                                                                    time=date_1)
        self.assertEqual(len(fwd_curves), 2)
        self.assertEqual(len(actual_dates), 2)
        self.assertTrue(EURUSD in fwd_curves)
        self.assertTrue(USDHKD in fwd_curves)
        eurusd_fwd = fwd_curves[EURUSD]
        usdhkd_fwd = fwd_curves[USDHKD]
        self.assertTrue(eurusd_fwd is not None)
        self.assertTrue(usdhkd_fwd is not None)
        self.assertEqual(eurusd_fwd.ref_date, date_1)
        self.assertEqual(usdhkd_fwd.ref_date, date_1)
        self.assertAlmostEqual(eurusd_fwd.at_Days(7) - eurusd_fwd.spot(), 0.01, delta=1.e-5)


if __name__ == '__main__':
    unittest.main()
