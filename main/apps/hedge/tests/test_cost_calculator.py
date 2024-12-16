import unittest

from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache, SpotFxCache
from hdlib.Core.FxPair import FxPair as FxPairHDL

from main.apps.account.models.test.base import BaseTestCase
from main.apps.hedge.models import CurrencyMargin, InterestRate
from main.apps.hedge.services.roll_cost_what_if import RatesCache
from main.apps.hedge.calculators.cost import StandardRollCostCalculator


class StandardCostCalculatorTestCase(BaseTestCase):

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

    def make_spot_fx_cache(self, date: Date) -> SpotFxCache:
        return DictSpotFxCache(date=date,
                               spots={'GBP/USD': 1.2,
                                      'USD/EUR': 0.9})

    def test_get_interest(self):
        cost_calculator = StandardRollCostCalculator()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 20
        cashflow_date = date + days_away

        spot_fx_cache = self.make_spot_fx_cache(date=date)
        rates_cache = self.make_rates_cache()

        amount_gbp = 1000

        dc = DayCounter_HD()

        # Test Positive Interest
        ttm = dc.year_fraction(start=date, end=cashflow_date)
        true_interest = 0.01 * ttm * amount_gbp  # A positive amount, its interest earned
        interest = cost_calculator.get_interest(amount=amount_gbp,
                                                start_date=date,
                                                end_date=cashflow_date,
                                                dc=dc,
                                                currency=self.gbp, rates_cache=rates_cache)

        self.assertAlmostEqual(interest, true_interest, 12)

        # Test Positive interest in domestic
        interest_domestic = cost_calculator.get_interest_in_domestic(domestic=self.usd,
                                                                     cash_currency=self.gbp,
                                                                     amount=amount_gbp,
                                                                     start_date=date,
                                                                     end_date=cashflow_date,
                                                                     dc=dc,
                                                                     spot_fx_cache=spot_fx_cache,
                                                                     rates_cache=rates_cache)
        self.assertAlmostEqual(interest_domestic, true_interest * 1.2, 12)

        # Test Negative Interest
        amount_gbp = -1000
        ttm = dc.year_fraction(start=date, end=cashflow_date)
        true_interest = 0.02 * ttm * amount_gbp  # a negative amount, its interest paid
        interest = cost_calculator.get_interest(amount=amount_gbp,
                                                start_date=date,
                                                end_date=cashflow_date,
                                                dc=dc,
                                                currency=self.gbp, rates_cache=rates_cache)

        self.assertAlmostEqual(interest, true_interest, 12)

        # Test Negative interest in domestic
        interest_domestic = cost_calculator.get_interest_in_domestic(domestic=self.usd,
                                                                     cash_currency=self.gbp,
                                                                     amount=amount_gbp,
                                                                     start_date=date,
                                                                     end_date=cashflow_date,
                                                                     dc=dc,
                                                                     spot_fx_cache=spot_fx_cache,
                                                                     rates_cache=rates_cache)
        self.assertAlmostEqual(interest_domestic, true_interest * 1.2, 12)

    def test_get_roll_rates(self):
        cost_calculator = StandardRollCostCalculator()

        date = Date.create(year=2020, month=1, day=1)
        days_away = 1
        cashflow_date = date + days_away

        rates_cache = self.make_rates_cache()

        dc = DayCounter_HD()

        fx_pair = FxPairHDL(base=self.gbp, quote=self.usd)
        fx_spot = 1.2

        roll_rate_long, roll_rate_short = cost_calculator.get_roll_rates_for_fx_position(
            start_date=date,
            end_date=cashflow_date,
            dc=dc,
            fx_pair=fx_pair,
            fx_spot=fx_spot,
            rates_cache=rates_cache)

        ttm = dc.year_fraction_from_days(days_away)
        roll_long = ttm * fx_spot * (0.01 - 0.06)
        self.assertAlmostEqual(roll_rate_long, roll_long, 12)

        roll_short = ttm * fx_spot * (-0.02 + 0.03)
        self.assertAlmostEqual(roll_rate_short, roll_short, 12)

        # Now calculate the roll cost of a long and short position
        cost_long = cost_calculator.get_roll_cost_for_fx_position(
            start_date=date,
            end_date=cashflow_date,
            dc=dc,
            fx_pair=fx_pair,
            fx_spot=fx_spot,
            rates_cache=rates_cache,
            amount=1000)
        self.assertAlmostEqual(cost_long, 1000*roll_long)

        # Now calculate the roll cost of a long and short position
        cost_short = cost_calculator.get_roll_cost_for_fx_position(
            start_date=date,
            end_date=cashflow_date,
            dc=dc,
            fx_pair=fx_pair,
            fx_spot=fx_spot,
            rates_cache=rates_cache,
            amount=-1000)
        self.assertAlmostEqual(cost_short, 1000*roll_short)


if __name__ == '__main__':
    unittest.main()
