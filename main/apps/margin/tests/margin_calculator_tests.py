import unittest

from django.test import testcases
from hdlib.Core.Currency import USD, EUR
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache, DictSpotFxCache

from main.apps.broker.models import Broker
from main.apps.margin.services.calculators.ibkr import IBMarginCalculator
from main.apps.margin.services.calculators import MarginRatesCache


class MarginCalculatorTest(testcases.TestCase):
    def test_compute_required_cash_deposit_no_deposit(self):
        date = Date.today()
        cash_positions = CashPositions()
        cash_positions.add_cash(currency=USD, amount=480000)
        cash_positions.add_cash(currency=EUR, amount=-250000)
        spot_fx_cache = DictSpotFxCache(date, {"EUR/USD": 1.2, "USD/EUR": 0.8})
        broker = Broker()
        margin_rate_cash = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache)

        margin_calculator = IBMarginCalculator()
        required_deposit = margin_calculator.compute_required_cash_deposit_or_withdrawl(
            cash_positions=cash_positions,
            domestic=USD,
            spot_fx_cache=spot_fx_cache,
            margin_rates=margin_rate_cash,
            target_health=0.5)
        self.assertEqual(required_deposit, -90000)

    def test_compute_required_cash_deposit_some_deposit(self):
        date = Date.today()
        cash_positions = CashPositions()
        cash_positions.add_cash(currency=USD, amount=300000)
        cash_positions.add_cash(currency=EUR, amount=-250000)
        spot_fx_cache = DictSpotFxCache(date, {"EUR/USD": 1.2, "USD/EUR": 0.8})
        broker = Broker()
        margin_rate_cash = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache)

        margin_calculator = IBMarginCalculator()
        required_deposit = margin_calculator.compute_required_cash_deposit_or_withdrawl(
            cash_positions=cash_positions,
            domestic=USD,
            spot_fx_cache=spot_fx_cache,
            margin_rates=margin_rate_cash,
            target_health=0.5)
        self.assertEqual(required_deposit, 90000)


if __name__ == '__main__':
    unittest.main()
