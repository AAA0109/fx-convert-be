import unittest

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import CashFlow
from main.apps.account.models.test.base import BaseTestCase
from main.apps.hedge.models import CurrencyMargin, InterestRate
from main.apps.hedge.services.roll_cost_what_if import RollCostWhatIfService, RatesCache


class RollCostWhatIfTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def make_rates_cache(self) -> RatesCache:
        interest_rate_tiers = {
            self.gbp: [InterestRate(tier_from=0, tier_to=None, rate=0.01)],
            self.euro: [InterestRate(tier_from=0, tier_to=None, rate=0.02)],
            self.usd: [InterestRate(tier_from=0, tier_to=None, rate=0.03)]
        }

        loan_rate_tiers = {
            self.gbp: [CurrencyMargin(tier_from=0, tier_to=None, rate=0.02)],
            self.euro: [CurrencyMargin(tier_from=0, tier_to=None, rate=0.04)],
            self.usd: [CurrencyMargin(tier_from=0, tier_to=None, rate=0.06)]
        }

        return RatesCache(interest_rate_tiers=interest_rate_tiers,
                          loan_rate_tiers=loan_rate_tiers)

    def test_fee_whatif_one_negative_cashflow(self):
        what_if_service = RollCostWhatIfService()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 20
        cashflow_date = date + days_away

        cashflow = CashFlow.create_cashflow(account=self.account11, date=cashflow_date, currency=self.gbp,
                                            amount=-1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        spot_fx_cache = DictSpotFxCache(date=date, spots={'GBP/USD': 1.2})
        rates_cache = self.make_rates_cache()

        details = what_if_service.get_roll_cost_estimate_what_if_after_trades(date=date,
                                                                              company=self.company1,
                                                                              new_cashflows=[cashflow],
                                                                              spot_fx_cache=spot_fx_cache,
                                                                              rates_cache=rates_cache)

        amount = 1000
        amount_usd = 1.2 * amount
        hedge_amount = -amount_usd  # we pay roll cost based on our hedge
        daily_roll = (0.01 - 0.06)  # NOTE: we are long GBP and short USD, since we are buying to hedge -cashflow
        total_cost = hedge_amount * daily_roll * days_away / 365

        self.assertTrue(total_cost > 0)  # We expect to pay a cost (POSITIVE), b/c GBP earns less than we pay on USD
        self.assertEqual(details.num_cashflows, 1)
        self.assertAlmostEqual(details.cost_total, total_cost, 12)
        self.assertEqual(details.cashflow_total, amount_usd)

    def test_fee_whatif_one_positive_cashflow(self):
        what_if_service = RollCostWhatIfService()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 20
        cashflow_date = date + days_away

        cashflow = CashFlow.create_cashflow(account=self.account11, date=cashflow_date, currency=self.gbp,
                                            amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        spot_fx_cache = DictSpotFxCache(date=date, spots={'GBP/USD': 1.2})
        rates_cache = self.make_rates_cache()

        details = what_if_service.get_roll_cost_estimate_what_if_after_trades(date=date,
                                                                              company=self.company1,
                                                                              new_cashflows=[cashflow],
                                                                              spot_fx_cache=spot_fx_cache,
                                                                              rates_cache=rates_cache)

        amount = 1000
        amount_usd = 1.2 * amount
        # We are short GBP (pay 2%, and long USD, ear 3%)
        daily_roll = (0.03 - 0.02)
        hedge_amount = amount_usd  # we pay roll cost based on our hedge
        total_cost = hedge_amount * daily_roll * days_away / 365
        total_cost = -total_cost  # SINCE we represent costs as POSTIVE, and gains as NEGATIVE costs

        self.assertTrue(total_cost < 0)  # We expect to earn money in this case, so cost is negative
        self.assertEqual(details.num_cashflows, 1)
        self.assertAlmostEqual(details.cost_total, total_cost, 12)
        self.assertEqual(details.cashflow_total, amount_usd)


if __name__ == '__main__':
    unittest.main()
