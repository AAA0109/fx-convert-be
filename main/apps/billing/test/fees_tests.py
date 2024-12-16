import unittest

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import CashFlow
from main.apps.account.models.test.base import BaseTestCase
from main.apps.billing.models.fee import Fee
from main.apps.billing.services.fee import FeeProviderService
from main.apps.billing.services.new_cash_fee import NewCashFeeService
from main.apps.billing.services.aum_fee import AumFeeRecorderDB


class FeeTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_maintenance_fee_lifecycle(self):
        fee_provider = FeeProviderService()
        fee_creator = AumFeeRecorderDB()

        date = Date.create(year=2020, month=1, day=1)
        due = date + 20
        fee = fee_creator.create_maintenance_fee(amount=1000, incurred=date, due=due, company=self.company1)
        self.assertEqual(fee.status, Fee.Status.DUE)
        self.assertEqual(Date.to_date(fee.due), due)
        self.assertEqual(Date.to_date(fee.incurred), date)
        self.assertEqual(None, fee.settled)
        self.assertEqual(fee.amount, 1000)

        fees = fee_provider.get_fees(company=self.company1)
        self.assertEqual(fees[0], fee)
        self.assertEqual(len(fees), 1)

        total = fee_provider.aggregate_fees_over_period(company=self.company1)
        self.assertEqual(total, 1000)

        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.DUE,))
        self.assertEqual(total, 1000)

        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.DUE,),
                                                        by_type=(Fee.FeeType.NEW_CASHFLOW,))
        self.assertEqual(total, 0)

        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.PAID,))
        self.assertEqual(total, 0)

        # Check due date property
        self.assertFalse(fee.is_overdue(date + 10))
        self.assertFalse(fee.is_overdue(due))
        self.assertTrue(fee.is_overdue(due + 1))

        # Settle the fee
        settle_on = date + 5
        fee.settle(datetime=settle_on)
        self.assertFalse(fee.is_overdue(due + 1))
        self.assertEqual(Date.to_date(fee.settled), settle_on)
        self.assertEqual(fee.status, Fee.Status.PAID)

        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.PAID,))
        self.assertEqual(total, 1000)

        # Add another fee
        fee = fee_creator.create_maintenance_fee(amount=1000, incurred=date, due=due, company=self.company1)
        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.PAID,))
        self.assertEqual(total, 1000)

        total = fee_provider.aggregate_fees_over_period(company=self.company1)
        self.assertEqual(total, 2000)

    def test_cashflow_amount(self):
        fee_creator = NewCashFeeService()

        spots = DictSpotFxCache(date=Date.create(year=2020, month=1, day=1),
                                spots={'GBP/USD': 1.1,
                                       'EUR/USD': 1.2})
        date = Date.create(year=2020, month=5, day=1)

        # Test raw cashflow
        cashflow = CashFlow.create_cashflow(account=self.account11, date=date, currency=self.gbp,
                                            amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        self.assertEqual(fee_creator._get_cashflow_amount_for_fee(cashflow=cashflow, spot_fx_cache=spots), 1100)

        due = date + 20
        fee = fee_creator.create_new_cashflow_fee(spot_fx_cache=spots, incurred=date, due=due, cashflow=cashflow)
        self.assertEqual(fee.status, Fee.Status.DUE)
        self.assertEqual(Date.to_date(fee.due), due)
        self.assertEqual(Date.to_date(fee.incurred), date)
        self.assertEqual(None, fee.settled)
        self.assertEqual(fee.amount, 1100)
        self.assertEqual(fee.cashflow, cashflow)

        # Test recurring cashflow
        cashflow = CashFlow.create_cashflow(account=self.account11, date=date,
                                            end_date=date + 16,
                                            currency="GBP", amount=-1000,
                                            periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                                            status=CashFlow.CashflowStatus.ACTIVE)
        self.assertEqual(fee_creator._get_cashflow_amount_for_fee(cashflow=cashflow, spot_fx_cache=spots), 2200)

    def test_new_cashflow_fee_lifecycle(self):
        fee_provider = FeeProviderService()
        fee_creator = NewCashFeeService()

        date = Date.create(year=2020, month=1, day=1)
        due = date + 20

        cashflow = CashFlow.create_cashflow(account=self.account11, date=date, currency=self.usd,
                                            amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        fee = fee_creator._create_new_cashflow_fee_from_amount(amount=1000, incurred=date, due=due, cashflow=cashflow)
        self.assertEqual(fee.status, Fee.Status.DUE)
        self.assertEqual(Date.to_date(fee.due), due)
        self.assertEqual(Date.to_date(fee.incurred), date)
        self.assertEqual(None, fee.settled)
        self.assertEqual(fee.amount, 1000)
        self.assertEqual(fee.cashflow, cashflow)

        # Settle the fee
        settle_on = date + 5
        fee.settle(datetime=settle_on)
        self.assertFalse(fee.is_overdue(due + 1))
        self.assertEqual(Date.to_date(fee.settled), settle_on)
        self.assertEqual(fee.status, Fee.Status.PAID)

        total = fee_provider.aggregate_fees_over_period(company=self.company1, by_status=(Fee.Status.PAID,))
        self.assertEqual(total, 1000)


if __name__ == '__main__':
    unittest.main()
