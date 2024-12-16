import unittest

from hdlib.DateTime.Date import Date

from main.apps.account.models import CashFlow, iter_active_cashflows

import django.test.testcases as testcases

from main.apps.account.models.test.base import BaseTestCase
from main.apps.currency.models import Currency

usd = Currency(symbol='$', mnemonic="USD", name="USD")
eur = Currency(symbol='E', mnemonic="EUR", name="EURO")


class CashFlowTestCase(testcases.SimpleTestCase):

    def test_iter_recurring(self):
        periodicity = "FREQ=MONTHLY;INTERVAL=1;BYMONTHDAY=7"

        cf = CashFlow(date=Date.create(2023, 2, 7, hour=9),
                      end_date=Date.create(2024, 1, 7, hour=9),
                      amount=-10000.0,
                      currency=usd,
                      periodicity=periodicity,
                      status=CashFlow.CashflowStatus.ACTIVE,
                      roll_convention=CashFlow.RollConvention.UNADJUSTED,
                      calendar=CashFlow.CalendarType.WESTERN_CALENDAR)
        self.assertEqual(cf.currency, usd)
        self.assertEqual(cf.date, Date.create(2023, 2, 7, hour=9))
        self.assertEqual(len([cf for cf in cf.get_hdl_cashflows()]), 12)
        self.assertEqual(cf.calendar, CashFlow.CalendarType.WESTERN_CALENDAR)
        self.assertEqual(cf.roll_convention, CashFlow.RollConvention.UNADJUSTED)
        self.assertEqual(cf.amount, -10000.0)
        self.assertEqual(cf.periodicity, periodicity)

        # Test case where the nearest date pushes one of the cashflows to fall after end date, resulting in 11 not 12
        cf = CashFlow(date=Date.create(2023, 2, 7, hour=9),
                      end_date=Date.create(2024, 1, 7, hour=9),
                      amount=-10000.0,
                      currency=eur,
                      periodicity=periodicity,
                      status=CashFlow.CashflowStatus.ACTIVE,
                      roll_convention=CashFlow.RollConvention.NEAREST,
                      calendar=CashFlow.CalendarType.WESTERN_CALENDAR)
        self.assertEqual(cf.currency, eur)
        self.assertEqual(cf.calendar, CashFlow.CalendarType.WESTERN_CALENDAR)
        self.assertEqual(cf.roll_convention, CashFlow.RollConvention.NEAREST)
        self.assertEqual(len([cf for cf in cf.get_hdl_cashflows()]), 11)

    def test_iter_cashflow_expires_today(self):
        cf1 = CashFlow(amount=100, currency=usd, date=Date.create(2020, 1, 1))
        cfs = [cf1]

        iterated_cfs = list(iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 1)))
        self.assertEqual(0, len(iterated_cfs))
        iterated_cfs = list(iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 1), include_cashflows_on_vd=True))
        self.assertEqual(1, len(iterated_cfs))
        self.assertEqual(cf1.name, iterated_cfs[0].name)
        self.assertEqual(cf1.amount, iterated_cfs[0].amount)
        self.assertEqual(cf1.currency, iterated_cfs[0].currency)
        self.assertEqual(cf1.date.toordinal(), iterated_cfs[0].pay_date.toordinal())

    def test_iter_cashflow_only_one(self):
        cf1 = CashFlow(amount=100, currency=usd, date=Date.create(2020, 1, 2))
        cfs = [cf1]
        iterated_cfs = list(
            iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 1), include_cashflows_on_vd=False))
        self.assertEqual(cf1.name, iterated_cfs[0].name)
        self.assertEqual(cf1.amount, iterated_cfs[0].amount)
        self.assertEqual(cf1.currency, iterated_cfs[0].currency)
        self.assertEqual(cf1.date.toordinal(), iterated_cfs[0].pay_date.toordinal())

    def test_iter_cashflow_multiple_no_recurring(self):
        cf1 = CashFlow(amount=100, currency=usd, date=Date.create(2020, 1, 1), name="cf1")
        cf2 = CashFlow(amount=200, currency=usd, date=Date.create(2020, 1, 2), name="cf2")
        cf3 = CashFlow(amount=300, currency=usd, date=Date.create(2020, 1, 3), name="cf3")
        cf4 = CashFlow(amount=400, currency=usd, date=Date.create(2020, 1, 4), name="cf4")
        cfs = [cf1, cf2, cf3, cf4]
        iterated_cfs = list(
            iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 2, ), include_cashflows_on_vd=False))
        self.assertEqual(2, len(iterated_cfs))
        self.assertEqual(cf3.name, iterated_cfs[0].name)
        self.assertEqual(cf3.amount, iterated_cfs[0].amount)
        self.assertEqual(cf3.currency, iterated_cfs[0].currency)
        self.assertEqual(cf3.date.toordinal(), iterated_cfs[0].pay_date.toordinal())
        self.assertEqual(cf4.name, iterated_cfs[1].name)
        self.assertEqual(cf4.amount, iterated_cfs[1].amount)
        self.assertEqual(cf4.currency, iterated_cfs[1].currency)
        self.assertEqual(cf4.date.toordinal(), iterated_cfs[1].pay_date.toordinal())

        iterated_cfs = list(iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 2), include_cashflows_on_vd=True))
        self.assertEqual(3, len(iterated_cfs))
        self.assertEqual(cf2.name, iterated_cfs[0].name)
        self.assertEqual(cf2.amount, iterated_cfs[0].amount)
        self.assertEqual(cf2.currency, iterated_cfs[0].currency)
        self.assertEqual(cf2.date.toordinal(), iterated_cfs[0].pay_date.toordinal())
        self.assertEqual(cf3.name, iterated_cfs[1].name)
        self.assertEqual(cf3.amount, iterated_cfs[1].amount)
        self.assertEqual(cf3.currency, iterated_cfs[1].currency)
        self.assertEqual(cf3.date.toordinal(), iterated_cfs[1].pay_date.toordinal())
        self.assertEqual(cf4.name, iterated_cfs[2].name)
        self.assertEqual(cf4.amount, iterated_cfs[2].amount)
        self.assertEqual(cf4.currency, iterated_cfs[2].currency)
        self.assertEqual(cf4.date.toordinal(), iterated_cfs[2].pay_date.toordinal())

        iterated_cfs = list(iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 3), include_cashflows_on_vd=True,
                                                  max_date_in_future=Date.create(2020, 1, 3), include_end=True))
        self.assertEqual(1, len(iterated_cfs))
        self.assertEqual(cf3.name, iterated_cfs[0].name)
        self.assertEqual(cf3.amount, iterated_cfs[0].amount)
        self.assertEqual(cf3.currency, iterated_cfs[0].currency)
        self.assertEqual(cf3.date, iterated_cfs[0].pay_date)

        iterated_cfs = list(iter_active_cashflows(cfs, ref_date=Date.create(2020, 1, 3), include_cashflows_on_vd=True,
                                                  max_date_in_future=Date.create(2020, 1, 4), include_end=True))
        self.assertEqual(2, len(iterated_cfs))
        self.assertEqual(cf3.name, iterated_cfs[0].name)
        self.assertEqual(cf3.amount, iterated_cfs[0].amount)
        self.assertEqual(cf3.currency, iterated_cfs[0].currency)
        self.assertEqual(cf3.date, iterated_cfs[0].pay_date)
        self.assertEqual(cf4.name, iterated_cfs[1].name)
        self.assertEqual(cf4.amount, iterated_cfs[1].amount)
        self.assertEqual(cf4.currency, iterated_cfs[1].currency)
        self.assertEqual(cf4.date, iterated_cfs[1].pay_date)


class UpdatePendingCashFlowTestCase(BaseTestCase):
    def test_update(self):
        cfs = []
        cf11 = CashFlow.create_cashflow(
            account=self.account11,
            amount=100,
            currency=usd,
            date=Date.create(2020, 1, 1),
            name="cf1", status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        cfs.append(cf11)
        cf12 = CashFlow.create_cashflow(
            account=self.account11,
            amount=200,
            currency=usd,
            date=Date.create(2020, 1, 2),
            name="cf2",
            status=CashFlow.CashflowStatus.ACTIVE)
        cfs.append(cf12)
        cf13 = CashFlow.create_cashflow(
            account=self.account11,
            amount=300,
            currency=usd,
            date=Date.create(2020, 1, 3), name="cf3",
            status=CashFlow.CashflowStatus.PENDING_DEACTIVATION)
        cfs.append(cf13)
        cf14 = CashFlow.create_cashflow(
            account=self.account12,
            amount=400,
            currency=usd,
            date=Date.create(2020, 1, 4), name="cf4",
            status=CashFlow.CashflowStatus.INACTIVE)
        cfs.append(cf14)
        cf21 = CashFlow.create_cashflow(
            account=self.account21,
            amount=100,
            currency=usd,
            date=Date.create(2020, 1, 1),
            name="cf1", status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        cfs.append(cf21)
        cf22 = CashFlow.create_cashflow(
            account=self.account21,
            amount=200,
            currency=usd,
            date=Date.create(2020, 1, 2),
            name="cf2",
            status=CashFlow.CashflowStatus.ACTIVE)
        cfs.append(cf22)
        cf23 = CashFlow.create_cashflow(
            account=self.account21,
            amount=300,
            currency=usd,
            date=Date.create(2020, 1, 3), name="cf3",
            status=CashFlow.CashflowStatus.PENDING_DEACTIVATION)
        cfs.append(cf23)
        cf24 = CashFlow.create_cashflow(
            account=self.account21,
            amount=400,
            currency=usd,
            date=Date.create(2020, 1, 4), name="cf4",
            status=CashFlow.CashflowStatus.INACTIVE)
        cfs.append(cf24)

        CashFlow.update_pending_cashflows(company=self.company1)
        for cf in cfs:
            cf.refresh_from_db()
        self.assertEqual(CashFlow.CashflowStatus.ACTIVE, cf11.status)
        self.assertEqual(CashFlow.CashflowStatus.ACTIVE, cf12.status)
        self.assertEqual(CashFlow.CashflowStatus.INACTIVE, cf13.status)
        self.assertEqual(CashFlow.CashflowStatus.INACTIVE, cf14.status)

        self.assertEqual(CashFlow.CashflowStatus.PENDING_ACTIVATION, cf21.status)
        self.assertEqual(CashFlow.CashflowStatus.ACTIVE, cf22.status)
        self.assertEqual(CashFlow.CashflowStatus.PENDING_DEACTIVATION, cf23.status)
        self.assertEqual(CashFlow.CashflowStatus.INACTIVE, cf24.status)


if __name__ == '__main__':
    unittest.main()
