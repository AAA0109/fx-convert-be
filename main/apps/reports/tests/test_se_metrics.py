import pandas as pd
from django.test import TestCase

from main.apps.reports.services.stratex.performance import SEMetrics


class TestSEMetrics(TestCase):

    def setUp(self):
        data = {
            'rate_ask_ex': [100, 150, 200],
            'rate_bid_ex': [95, 145, 190],
            'rate_ask_start': [105, 155, 205],
            'rate_bid_start': [90, 140, 185],
            'start_time': pd.to_datetime(['2023-01-01 00:00', '2023-01-02 00:00', '2023-01-03 00:00']),
            'ex_time': pd.to_datetime(['2023-01-01 03:00', '2023-01-02 03:00', '2023-01-03 03:00'])
        }
        self.df = pd.DataFrame(data)
        self.metrics = SEMetrics(self.df)

    def test_average_buy(self):
        expected = 150
        result = self.metrics.average_buy()
        self.assertEqual(expected, result)

    def test_average_sell(self):
        expected = 143.33333333333334
        result = self.metrics.average_sell()
        self.assertEqual(expected, result)

    def test_average_buy_saved(self):
        expected = 5.0
        result = self.metrics.average_buy_saved()
        self.assertEqual(expected, result)

    def test_average_sell_gained(self):
        expected = 5.0
        result = self.metrics.average_sell_gained()
        self.assertEqual(expected, result)

    def test_average_saved(self):
        expected = 5.0
        result = self.metrics.average_saved()
        self.assertEqual(expected, result)

    def test_min_buy_saved(self):
        expected = 5.0
        result = self.metrics.min_buy_saved()
        self.assertEqual(expected, result)

    def test_min_sell_gained(self):
        expected = 5.0
        result = self.metrics.min_sell_gained()
        self.assertEqual(expected, result)

    def test_validate_dataframe_exception(self):
        with self.assertRaises(ValueError):
            SEMetrics(pd.DataFrame({'invalid_column': [1, 2, 3]}))
