import unittest

import numpy as np
from django.test import testcases
from hdlib.DateTime.DayCounter import DayCounter_HD

from hdlib.DateTime.Date import Date
from main.apps.currency.models import Currency
from main.apps.marketdata.models import IrDiscount, DataCut, IrCurve, BasisConvention
from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService


class HedgePositionServiceTest(testcases.TestCase):
    # noinspection DuplicatedCode
    def test__get_most_recent_discount_curves(self):
        date_1 = Date.create(ymd=2020_01_01, hour=23)
        date_2 = Date.create(ymd=2020_01_02, hour=23)
        date_3 = Date.create(ymd=2020_01_05, hour=23)

        cut_1 = DataCut.create_cut(time=date_1, cut_type=DataCut.CutType.EOD)
        cut_2 = DataCut.create_cut(time=date_2, cut_type=DataCut.CutType.EOD)
        cut_3 = DataCut.create_cut(time=date_3, cut_type=DataCut.CutType.EOD)

        _, USD = Currency.create_currency(mnemonic="USD", name="US Dollars")
        _, EUR = Currency.create_currency(mnemonic="EUR", name="Euros")
        _, HKD = Currency.create_currency(mnemonic="HKD", name="Hong Kong Dollars")

        ois_usd = IrCurve.create_curve(currency=USD,
                                       family=IrCurve.Family.OIS,
                                       name="USD thing",
                                       long_name="Long",
                                       basis_convention=BasisConvention.ACT_365)
        ois_eur = IrCurve.create_curve(currency=EUR,
                                       family=IrCurve.Family.OIS,
                                       name="EUR thing",
                                       long_name="Long",
                                       basis_convention=BasisConvention.ACT_365)
        ois_hkd = IrCurve.create_curve(currency=HKD,
                                       family=IrCurve.Family.OIS,
                                       name="HKD thing",
                                       long_name="Long",
                                       basis_convention=BasisConvention.ACT_365)

        dt = [7, 14, 21, 30, 45, 60, 90]
        maturities_1 = [date_1 + t for t in dt]
        maturities_2 = [date_2 + t for t in dt]
        maturities_3 = [date_3 + t for t in dt]

        discounts_1 = [0.995, 0.980, 0.975, 0.96, 0.954, 0.943, 0.940]
        discounts_2 = [0.988, 0.977, 0.975, 0.96, 0.950, 0.940, 0.938]

        dc = DayCounter_HD()
        IrDiscount.create_discount_curve(data_cut=cut_1, maturities=maturities_1, discounts=discounts_1,
                                         curve=ois_usd, dc=dc)
        IrDiscount.create_discount_curve(data_cut=cut_2, maturities=maturities_2, discounts=discounts_2,
                                         curve=ois_usd, dc=dc)
        IrDiscount.create_discount_curve(data_cut=cut_3, maturities=maturities_3, discounts=discounts_1,
                                         curve=ois_eur, dc=dc)

        ref_date = date_3 + 1
        # Test where we request by curve
        curves, actual_dates = MdIrProviderService.get_most_recent_discount_curves(ir_curves=[ois_usd, ois_eur],
                                                                                   time=ref_date)
        self.assertEqual(len(curves), 2)
        self.assertTrue(ois_usd.id in curves)
        self.assertTrue(ois_eur.id in curves)
        usd_curve = curves[ois_usd.id]
        eur_curve = curves[ois_eur.id]
        self.assertEqual(actual_dates[ois_usd.id], date_2)
        self.assertEqual(actual_dates[ois_eur.id], date_3)
        self.assertEqual(usd_curve.ref_date, ref_date)
        self.assertEqual(eur_curve.ref_date, ref_date)
        self.assertEqual(usd_curve.at_D(Date.from_datetime(usd_curve.ref_date) + 7), 0.988)
        self.assertEqual(eur_curve.at_D(Date.from_datetime(eur_curve.ref_date) + 7), 0.995)

        # Test where we request by curve id
        curves, actual_dates = MdIrProviderService.get_most_recent_discount_curves(ir_curves=[ois_usd.id, ois_eur.id],
                                                                                   time=ref_date)
        self.assertEqual(len(curves), 2)
        self.assertTrue(ois_usd.id in curves)
        self.assertTrue(ois_eur.id in curves)
        usd_curve = curves[ois_usd.id]
        eur_curve = curves[ois_eur.id]
        self.assertEqual(actual_dates[ois_usd.id], date_2)
        self.assertEqual(actual_dates[ois_eur.id], date_3)
        self.assertEqual(usd_curve.ref_date, ref_date)
        self.assertEqual(eur_curve.ref_date, ref_date)
        self.assertEqual(usd_curve.at_D(Date.from_datetime(usd_curve.ref_date) + 7), 0.988)
        self.assertEqual(eur_curve.at_D(Date.from_datetime(eur_curve.ref_date) + 7), 0.995)

        # Another test
        ref_date = date_1
        curves, actual_dates = MdIrProviderService.get_most_recent_discount_curves(ir_curves=[ois_usd, ois_hkd],
                                                                                   time=date_1)
        self.assertEqual(len(curves), 2)
        self.assertTrue(ois_usd.id in curves)
        self.assertTrue(ois_hkd.id in curves)
        usd_curve = curves[ois_usd.id]
        self.assertEqual(usd_curve.ref_date, ref_date)
        self.assertEqual(curves[ois_hkd.id], None)


if __name__ == '__main__':
    unittest.main()
