import unittest

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import CashFlow
from main.apps.account.models.test.base import BaseTestCase
from main.apps.billing.services.what_if import FeeWhatIfService
from main.apps.billing.models.fee_tier import FeeTier


class FeeWhatIfTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_fee_whatif_one_cashflow(self):
        new_cash_fee_rate = 0.05
        aum_fee_rate = 0.01

        FeeTier.create_tier(tier_from=0., company=self.company1,
                            new_cash_fee_rate=new_cash_fee_rate, aum_fee_rate=aum_fee_rate)

        what_if_service = FeeWhatIfService()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 20
        cashflow_date = date + days_away

        cashflow = CashFlow.create_cashflow(account=self.account11, date=cashflow_date, currency=self.gbp,
                                            amount=-1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        spot_fx_cache = DictSpotFxCache(date=date, spots={'GBP/USD': 1.2})

        details = what_if_service.get_fee_details_what_if_after_new_cashflows(date=date,
                                                                              company=self.company1,
                                                                              new_cashflows=[cashflow],
                                                                              spot_fx_cache=spot_fx_cache)

        amount_usd = 1200

        self.assertEqual(details.aum_fee_rate, aum_fee_rate)
        self.assertEqual(details.num_cashflows, 1)
        self.assertEqual(details.new_cashflow_fee_rate, new_cash_fee_rate)
        self.assertEqual(details.cashflow_total, amount_usd)
        self.assertEqual(details.aum_total_fee, days_away * amount_usd * aum_fee_rate / 365)
        self.assertEqual(details.new_cashflow_fee, amount_usd * new_cash_fee_rate)
        self.assertEqual(details.maturity_days, days_away)
        self.assertEqual(details.previous_rolling_aum, 0.)
        self.assertEqual(details.previous_daily_aum, 0.)

    def test_fee_whatif_one_recurring_cashflow(self):
        new_cash_fee_rate = 0.05
        aum_fee_rate = 0.01

        FeeTier.create_tier(tier_from=0., company=self.company1,
                            new_cash_fee_rate=new_cash_fee_rate, aum_fee_rate=aum_fee_rate)

        what_if_service = FeeWhatIfService()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 365
        last_date = date + days_away

        cashflow = CashFlow.create_cashflow(account=self.account11, date=date+28, currency=self.gbp,
                                            end_date=last_date,
                                            amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION,
                                            periodicity="FREQ=MONTHLY;INTERVAL=1")

        spot_fx_cache = DictSpotFxCache(date=date, spots={'GBP/USD': 1.2})

        details = what_if_service.get_fee_details_what_if_after_new_cashflows(date=date,
                                                                              company=self.company1,
                                                                              new_cashflows=[cashflow],
                                                                              spot_fx_cache=spot_fx_cache)

        amount_usd = 1.2*1000*12

        self.assertEqual(details.aum_fee_rate, aum_fee_rate)
        self.assertEqual(details.num_cashflows, 12)
        self.assertEqual(details.new_cashflow_fee_rate, new_cash_fee_rate)
        self.assertEqual(details.cashflow_total, amount_usd)
        self.assertEqual(details.new_cashflow_fee, amount_usd * new_cash_fee_rate)
        self.assertEqual(details.maturity_days, 363)
        self.assertEqual(details.aum_total_fee, 77.06301369863014)
        self.assertEqual(details.previous_rolling_aum, 0.)
        self.assertEqual(details.previous_daily_aum, 0.)

    def test_fee_whatif_multi_cashflow(self):
        new_cash_fee_rate = 0.05
        aum_fee_rate = 0.01

        FeeTier.create_tier(tier_from=0., company=self.company1,
                            new_cash_fee_rate=new_cash_fee_rate, aum_fee_rate=aum_fee_rate)

        what_if_service = FeeWhatIfService()

        date = Date.create(year=2020, month=1, day=1)
        days_away1 = 20
        days_away2 = 20
        days_away3 = 40
        cashflow_date1 = date + days_away1
        cashflow_date2 = date + days_away2
        cashflow_date3 = date + days_away3

        # Three cashflows, put into 2 accounts
        cashflow1 = CashFlow.create_cashflow(account=self.account11, date=cashflow_date1, currency=self.gbp,
                                             amount=-1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        cashflow2 = CashFlow.create_cashflow(account=self.account11, date=cashflow_date2, currency=self.gbp,
                                             amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        cashflow3 = CashFlow.create_cashflow(account=self.account12, date=cashflow_date3, currency=self.euro,
                                             amount=10000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        spot_fx_cache = DictSpotFxCache(date=date, spots={'GBP/USD': 1.2, 'USD/EUR': 0.9})

        details = what_if_service.get_fee_details_what_if_after_new_cashflows(
            date=date,
            company=self.company1,
            new_cashflows=[cashflow1, cashflow2, cashflow3],
            spot_fx_cache=spot_fx_cache)

        amount_usd = abs(cashflow1.amount) * 1.2 + abs(cashflow2.amount) * 1.2 + abs(cashflow3.amount) / 0.9

        self.assertEqual(details.aum_fee_rate, aum_fee_rate)
        self.assertEqual(details.num_cashflows, 3)
        self.assertEqual(details.new_cashflow_fee_rate, new_cash_fee_rate)
        self.assertEqual(details.cashflow_total, amount_usd)
        self.assertEqual(details.previous_rolling_aum, 0.)
        self.assertEqual(details.previous_daily_aum, 0.)

        aum_fee = aum_fee_rate * (abs(cashflow1.amount) * days_away1 * 1.2
                                  + abs(cashflow2.amount) * days_away2 * 1.2
                                  + abs(cashflow3.amount) * days_away3 / 0.9) / 365
        self.assertAlmostEqual(details.aum_total_fee, aum_fee)
        self.assertAlmostEqual(details.new_cashflow_fee, amount_usd * new_cash_fee_rate, 12)
        self.assertEqual(details.maturity_days, days_away3)
        self.assertEqual(details.cost_total, details.aum_total_fee + details.new_cashflow_fee)
        self.assertEqual(details.aum_fee_rate_of_cashflows, details.aum_total_fee / details.cashflow_total)


if __name__ == '__main__':
    unittest.main()
