import unittest

import numpy as np
from django.test import TestCase

from typing import Dict

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache, DictSpotFxCache

from hdlib.Core.CompanyInterface import BasicCompany

from hdlib.Core.AccountInterface import BasicAccount

from hdlib.Core.Currency import Currency, USD, EUR, GBP, JPY, ILS
from hdlib.Core.FxPair import FxPair
from main.apps.hedge.calculators.reconciliation import ReconciliationCalculator
from main.apps.hedge.support.account_hedge_interfaces import BasicAccountHedgeRequest
from main.apps.hedge.support.fx_fill_summary import FxFillSummary
from main.apps.hedge.support.fxposition_interface import BasicFxPosition
from main.apps.hedge.support.reconciliation_data import ReconciliationData


class CompanyHedgeCalculatorTest(TestCase):
    # noinspection DuplicatedCode
    def test__reconciliation_calculator__no_change(self):
        """
        Check that reconciliation works if nothing happens. This is the trivial case.
        """

        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000}
        company_positions_after = {EURUSD: 10_000, GBPUSD: 25_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account = BasicAccount(name="TEST", company=company)
        account_positions_by_fxpair = {EURUSD: {account: BasicFxPosition(EURUSD, 10_000, 10_000 * 1.1, account)},
                                       GBPUSD: {account: BasicFxPosition(EURUSD, 25_000, 25_000 * 1.1, account)}}

        desired_positions = {EURUSD: {account: 10_000}, GBPUSD: {account: 25_000}}

        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07})
        calculator = ReconciliationCalculator()
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         spot_cache=spot_cache)

        self.assertEqual(final_positions_by_fxpair[EURUSD][account].get_amount(), 10_000)
        self.assertEqual(final_positions_by_fxpair[GBPUSD][account].get_amount(), 25_000)
        self.assertEqual(len(account_hedge_results), 0)
        self.assertEqual(len(reconciliation_data), 2)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__perfect_order(self):
        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000}
        company_positions_after = {EURUSD: 10_000, GBPUSD: 20_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account = BasicAccount(name="TEST", company=company)
        account_positions_by_fxpair = {EURUSD: {account: BasicFxPosition(EURUSD, 10_000, 10_000 * 1.1, account)},
                                       GBPUSD: {account: BasicFxPosition(GBPUSD, 25_000, 25_000 * 1.1, account)}}

        account_hedge_requests = {EURUSD: [],
                                  GBPUSD: [BasicAccountHedgeRequest(fx_pair=GBPUSD, amount=-5_000, account=account)]}

        filled_amounts = {GBPUSD: FxFillSummary(amount_filled=-5_000, average_price=1.2,
                                                commission=0, cntr_commission=0)}

        desired_positions = {EURUSD: {account: 10_000}, GBPUSD: {account: 20_000}}

        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07})
        calculator = ReconciliationCalculator()
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        self.assertEqual(final_positions_by_fxpair[EURUSD][account].get_amount(), 10_000)
        self.assertEqual(final_positions_by_fxpair[GBPUSD][account].get_amount(), 20_000)
        self.assertEqual(len(account_hedge_results), 1)
        self.assertEqual(len(reconciliation_data), 2)

        # Check PnL
        self.assertAlmostEquals(account_hedge_results[0].get_pnl_quote(), 500, delta=1e-6)

        data: Dict[FxPair, ReconciliationData] = {datum.fx_pair: datum for datum in reconciliation_data}

        self.assertEqual(data[EURUSD].filled_amount, 0.0)
        self.assertEqual(data[EURUSD].excess_change, 0.0)

        self.assertEqual(data[GBPUSD].filled_amount, -5000.0)
        self.assertEqual(data[GBPUSD].excess_change, 0.0)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__test_pnl_calculation(self):
        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)
        USDJPY = FxPair(base=USD, quote=JPY)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000, USDJPY: 30_000}
        company_positions_after = {EURUSD: 10_150, GBPUSD: 20_000, USDJPY: 15_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account = BasicAccount(name="TEST", company=company)
        account_positions_by_fxpair = {EURUSD: {account: BasicFxPosition(EURUSD, 10_000, 10_000 * 1.110, account)},
                                       GBPUSD: {account: BasicFxPosition(GBPUSD, 25_000, 25_000 * 1.150, account)},
                                       USDJPY: {account: BasicFxPosition(USDJPY, 30_000, 30_000 * 115.00, account)}}

        account_hedge_requests = {EURUSD: [BasicAccountHedgeRequest(fx_pair=EURUSD, amount=150, account=account)],
                                  GBPUSD: [BasicAccountHedgeRequest(fx_pair=GBPUSD, amount=-5_000, account=account)],
                                  USDJPY: [BasicAccountHedgeRequest(fx_pair=USDJPY, amount=-15_000, account=account)]}

        filled_amounts = {EURUSD: FxFillSummary(amount_filled=150, average_price=1.120),
                          GBPUSD: FxFillSummary(amount_filled=-5_000, average_price=1.2),
                          USDJPY: FxFillSummary(amount_filled=-15_000, average_price=110.00)
                          }

        desired_positions = {EURUSD: {account: 10_150}, GBPUSD: {account: 20_000}, USDJPY: {account: 15_000}}

        # Expected PnL:
        #   EURUSD: Increased position => 0 PnL
        #   GBPUSD: Sold 5,000, D Ave Px = +0.05 => 250 PnL (USD)
        #   USDJPY: Sold 15,000, D Ave Px = -5.00 => -75,000 (JPY)

        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07, USDJPY: 115})
        calculator = ReconciliationCalculator()
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        # Check PnL
        results_by_fx = {result.get_request().get_fx_pair(): result for result in account_hedge_results}
        self.assertAlmostEquals(results_by_fx[EURUSD].pnl_quote, 0.0, delta=1e-6)
        self.assertAlmostEquals(results_by_fx[GBPUSD].pnl_quote, 250, delta=1e-6)
        self.assertAlmostEquals(results_by_fx[USDJPY].pnl_quote, -75_000, delta=1e-6)

        self.assertAlmostEquals(final_positions_by_fxpair[EURUSD][account].get_amount(), 10_150)
        self.assertAlmostEquals(final_positions_by_fxpair[GBPUSD][account].get_amount(), 20_000)
        self.assertAlmostEquals(final_positions_by_fxpair[USDJPY][account].get_amount(), 15_000)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__detect_excess_in_order(self):
        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000}
        company_positions_after = {EURUSD: 10_025, GBPUSD: 21_500}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        # Original account positions.
        account_positions_by_fxpair = {EURUSD: {account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                                                account2: BasicFxPosition(EURUSD, 2_500, 2_500 * 1.05, account2)},
                                       GBPUSD: {account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                                                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)}}

        account_hedge_requests = {
            EURUSD: [BasicAccountHedgeRequest(fx_pair=EURUSD, amount=-5_000, account=account1),
                     BasicAccountHedgeRequest(fx_pair=EURUSD, amount=+5_000, account=account2)],
            GBPUSD: [BasicAccountHedgeRequest(fx_pair=GBPUSD, amount=-3_000, account=account1),
                     BasicAccountHedgeRequest(fx_pair=GBPUSD, amount=-1_000, account=account2)]
        }

        filled_amounts = {GBPUSD: FxFillSummary(amount_filled=-5_000, average_price=1.2,
                                                commission=0.15, cntr_commission=0),
                          EURUSD: FxFillSummary(amount_filled=0, average_price=0,
                                                commission=0, cntr_commission=0),
                          }

        desired_positions = {EURUSD: {account1: 2_500, account2: 7_500}, GBPUSD: {account1: 17_000, account2: 4_000}}

        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07})
        calculator = ReconciliationCalculator()
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        self.assertEqual(final_positions_by_fxpair[EURUSD][account1].get_amount(), 2_506.25)
        self.assertEqual(final_positions_by_fxpair[EURUSD][account2].get_amount(), 7_518.75)
        self.assertAlmostEqual(final_positions_by_fxpair[GBPUSD][account1].get_amount(), 17_404.762, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[GBPUSD][account2].get_amount(), 4_095.238, delta=0.001)
        self.assertEqual(len(account_hedge_results), 4)
        self.assertEqual(len(reconciliation_data), 2)

        data: Dict[FxPair, ReconciliationData] = {datum.fx_pair: datum for datum in reconciliation_data}

        self.assertEqual(data[EURUSD].filled_amount, 5018.75)  # Excess counts as a fill.
        self.assertEqual(data[EURUSD].excess_change, 25)

        self.assertEqual(data[GBPUSD].filled_amount, -904.7619047619046)
        self.assertEqual(data[GBPUSD].excess_change, 500)
        self.assertEqual(data[GBPUSD].commission, 0.15)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__desired_positions(self):
        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000}
        company_positions_after = {EURUSD: 10_000, GBPUSD: 25_500}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        # Original account positions.
        account_positions_by_fxpair = {EURUSD: {account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                                                account2: BasicFxPosition(EURUSD, 2_500, 2_500 * 1.05, account2)},
                                       GBPUSD: {account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                                                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)}}

        account_hedge_requests = None
        filled_amounts = None
        calculator = ReconciliationCalculator()

        # Change so the desired positions do not match the company positions, make sure it divides the excess or
        # shortfall correctly.

        desired_positions = {EURUSD: {account1: 2_732.11, account2: 7_932.50},
                             GBPUSD: {account1: -1_223.3, account2: 25_400}}
        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07})
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        desired_eurusd = desired_positions[EURUSD][account1] + desired_positions[EURUSD][account2]
        abs_desired_eurusd = np.abs(desired_positions[EURUSD][account1]) + np.abs(desired_positions[EURUSD][account2])
        desired_gbpusd = desired_positions[GBPUSD][account1] + desired_positions[GBPUSD][account2]
        abs_desired_gbpusd = np.abs(desired_positions[GBPUSD][account1]) + np.abs(desired_positions[GBPUSD][account2])
        excess_eurusd = company_positions_after[EURUSD] - desired_eurusd
        excess_gbpusd = company_positions_after[GBPUSD] - desired_gbpusd

        w_1_eurusd = np.abs(desired_positions[EURUSD][account1]) / abs_desired_eurusd
        w_2_eurusd = np.abs(desired_positions[EURUSD][account2]) / abs_desired_eurusd
        w_1_gbpusd = np.abs(desired_positions[GBPUSD][account1]) / abs_desired_gbpusd
        w_2_gbpusd = np.abs(desired_positions[GBPUSD][account2]) / abs_desired_gbpusd

        expected_eurusd_1 = w_1_eurusd * excess_eurusd + desired_positions[EURUSD][account1]
        expected_eurusd_2 = w_2_eurusd * excess_eurusd + desired_positions[EURUSD][account2]

        expected_gbpusd_1 = w_1_gbpusd * excess_gbpusd + desired_positions[GBPUSD][account1]
        expected_gbpusd_2 = w_2_gbpusd * excess_gbpusd + desired_positions[GBPUSD][account2]

        self.assertAlmostEqual(expected_eurusd_1, final_positions_by_fxpair[EURUSD][account1].get_amount(),
                               delta=0.001)
        self.assertAlmostEqual(expected_eurusd_2, final_positions_by_fxpair[EURUSD][account2].get_amount(),
                               delta=0.001)
        self.assertAlmostEqual(expected_gbpusd_1, final_positions_by_fxpair[GBPUSD][account1].get_amount(),
                               delta=0.001)
        self.assertAlmostEqual(expected_gbpusd_2, final_positions_by_fxpair[GBPUSD][account2].get_amount(),
                               delta=0.001)

        self.assertAlmostEqual(final_positions_by_fxpair[EURUSD][account1].get_amount(), 2561.84708, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[EURUSD][account2].get_amount(), 7438.15292, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[GBPUSD][account1].get_amount(), -1162.49638, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[GBPUSD][account2].get_amount(), 26662.49638, delta=0.001)

        # Check that the total positions held by all accounts matches the total positions that the company holds.
        total = final_positions_by_fxpair[EURUSD][account1].get_amount() \
                + final_positions_by_fxpair[EURUSD][account2].get_amount()
        self.assertAlmostEquals(total, company_positions_after[EURUSD])
        total = final_positions_by_fxpair[GBPUSD][account1].get_amount() \
                + final_positions_by_fxpair[GBPUSD][account2].get_amount()
        self.assertAlmostEquals(total, company_positions_after[GBPUSD])

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__position_no_one_wants__same_position(self):
        # Test that something reasonable happens when we can't close a position.
        #
        # This tests the case where a position was held yesterday, and no one wants any of the FxPair today.
        # In this case, the accounts that held the position yesterday should be forced to continue holding that
        # position.
        #
        # Furthermore, in this case, the amount of position is the same as what existed today, so the accounts should
        # retain the same position as they did yesterday.

        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)
        ILSUSD = FxPair(base=ILS, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000, ILSUSD: 8_000}
        company_positions_after = {EURUSD: 10_500, GBPUSD: 25_500, ILSUSD: 8_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        account3 = BasicAccount(name="ACCOUNT_3", company=company)
        # Original account positions.
        account_positions_by_fxpair = {EURUSD:
            {
                account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                account2: BasicFxPosition(EURUSD, 2_000, 2_000 * 1.05, account2),
                account3: BasicFxPosition(EURUSD, 500, 500 * 1.05, account3)
            },
            GBPUSD: {
                account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)
            },
            ILSUSD: {
                account1: BasicFxPosition(ILSUSD, 15_000, 15_000 * 0.3, account1),
                account3: BasicFxPosition(ILSUSD, -7_000, 7_000 * 0.3, account3)
            }
        }

        account_hedge_requests = None
        filled_amounts = None
        calculator = ReconciliationCalculator()

        # Change so the desired positions do not match the company positions, make sure it divides the excess or
        # shortfall correctly.

        desired_positions = {
            EURUSD: {account1: 8_500, account2: 1_500, account3: 500},
            GBPUSD: {account1: 20_000, account2: 5_500},
            # No one wants ILS!!!
        }
        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07, ILSUSD: 0.3})
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        # Positions should remain the same.
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account1].get_amount(), 15_000, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account3].get_amount(), -7_000, delta=0.001)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__position_no_one_wants__different_position(self):
        # Test that something reasonable happens when we can't close a position.
        #
        # This tests the case where a position was held yesterday, and no one wants any of the FxPair today.
        # In this case, the accounts that held the position yesterday should be forced to continue holding that
        # position.
        #
        # In this case, for whatever reason, the amount of the unwanted pair changed from yesterday. Maybe we could
        # only liquidate part of the position. In this case, the positions should be similar to yesterday's positions,
        # but change by an amount proportional to the absolute value of yesterdays position.
        # See reconciliation_calculator for details.

        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)
        ILSUSD = FxPair(base=ILS, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000, ILSUSD: 8_000}
        company_positions_after = {EURUSD: 10_500, GBPUSD: 25_500, ILSUSD: 6_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        account3 = BasicAccount(name="ACCOUNT_3", company=company)
        # Original account positions.
        account_positions_by_fxpair = {EURUSD:
            {
                account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                account2: BasicFxPosition(EURUSD, 2_000, 2_000 * 1.05, account2),
                account3: BasicFxPosition(EURUSD, 500, 500 * 1.05, account2)
            },
            GBPUSD: {
                account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)
            },
            ILSUSD: {
                account1: BasicFxPosition(ILSUSD, 15_000, 15_000 * 0.3, account1),
                account3: BasicFxPosition(ILSUSD, -7_000, 7_000 * 0.3, account3)
            }
        }

        account_hedge_requests = None
        filled_amounts = None
        calculator = ReconciliationCalculator()

        # Change so the desired positions do not match the company positions, make sure it divides the excess or
        # shortfall correctly.

        desired_positions = {
            EURUSD: {account1: 8_500, account2: 1_500, account3: 500},
            GBPUSD: {account1: 20_000, account2: 5_500},
            # No one wants ILS!!!
        }
        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07, ILSUSD: 0.3})
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        # Positions should change somewhat.
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account1].get_amount(), 11_250, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account3].get_amount(), -5_250, delta=0.001)

    # noinspection DuplicatedCode
    def test__reconciliation_calculator__position_no_one_wants__position_direction_switches(self):
        # Test that something reasonable happens when we can't close a position.
        #
        # This tests the case where a position was held yesterday, and no one wants any of the FxPair today.
        # In this case, the accounts that held the position yesterday should be forced to continue holding that
        # position.
        #
        # In this case, for whatever reason, the amount of the unwanted pair not only changed from yesterday, but
        # switched sign.

        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)
        ILSUSD = FxPair(base=ILS, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000, ILSUSD: 8_000}
        company_positions_after = {EURUSD: 10_500, GBPUSD: 25_500, ILSUSD: -4_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        account3 = BasicAccount(name="ACCOUNT_3", company=company)
        # Original account positions.
        account_positions_by_fxpair = {
            EURUSD: {
                account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                account2: BasicFxPosition(EURUSD, 2_000, 2_000 * 1.05, account2),
                account3: BasicFxPosition(EURUSD, 500, 500 * 1.05, account2)
            },
            GBPUSD: {
                account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)
            },
            ILSUSD: {
                account1: BasicFxPosition(ILSUSD, 15_000, 15_000 * 0.3, account1),
                account3: BasicFxPosition(ILSUSD, -7_000, 7_000 * 0.3, account3)
            }
        }

        account_hedge_requests = None
        filled_amounts = None
        calculator = ReconciliationCalculator()

        # Change so the desired positions do not match the company positions, make sure it divides the excess or
        # shortfall correctly.

        desired_positions = {
            EURUSD: {account1: 8_500, account2: 1_500, account3: 500},
            GBPUSD: {account1: 20_000, account2: 5_500},
            # No one wants ILS!!!
        }
        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07, ILSUSD: 0.3})
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        # Positions should change somewhat.
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account1].get_amount(), -7_500, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account3].get_amount(), 3_500, delta=0.001)

        # noinspection DuplicatedCode

    def test__reconciliation_calculator__position_no_one_wants__new_position(self):
        # Test that something reasonable happens when a position just appears.
        #
        # This tests the case where a position was *not* held yesterday, and yet is a holding of the company today.

        EURUSD = FxPair(base=EUR, quote=USD)
        GBPUSD = FxPair(base=GBP, quote=USD)
        ILSUSD = FxPair(base=ILS, quote=USD)

        company_positions_before = {EURUSD: 10_000, GBPUSD: 25_000}
        company_positions_after = {EURUSD: 10_500, GBPUSD: 25_500, ILSUSD: 10_000}

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account1 = BasicAccount(name="ACCOUNT_1", company=company)
        account2 = BasicAccount(name="ACCOUNT_2", company=company)
        account3 = BasicAccount(name="ACCOUNT_3", company=company)
        # Original account positions.
        account_positions_by_fxpair = {EURUSD:
            {
                account1: BasicFxPosition(EURUSD, 7_500, 7_500 * 1.05, account1),
                account2: BasicFxPosition(EURUSD, 2_000, 2_000 * 1.05, account2),
                account3: BasicFxPosition(EURUSD, 500, 500 * 1.05, account2)
            },
            GBPUSD: {
                account1: BasicFxPosition(GBPUSD, 20_000, 20_000 * 1.07, account1),
                account2: BasicFxPosition(GBPUSD, 5_000, 5_000 * 1.07, account2)
            },
        }

        account_hedge_requests = None
        filled_amounts = None
        calculator = ReconciliationCalculator()

        # Change so the desired positions do not match the company positions, make sure it divides the excess or
        # shortfall correctly.

        desired_positions = {
            EURUSD: {account1: 8_500, account2: 1_500, account3: 500},
            GBPUSD: {account1: 20_000, account2: 5_500},
            # No one wants ILS!!!
        }
        spot_cache = DictSpotFxCache(date=Date.from_int(2023_01_01), spots={EURUSD: 1.05, GBPUSD: 1.07, ILSUSD: 0.3})
        final_positions_by_fxpair, reconciliation_data, account_hedge_results = \
            calculator.reconcile_company(company_positions_before=company_positions_before,
                                         company_positions_after=company_positions_after,
                                         account_desired_positions=desired_positions,
                                         initial_account_positions=account_positions_by_fxpair,
                                         account_hedge_requests=account_hedge_requests,
                                         filled_amounts=filled_amounts,
                                         spot_cache=spot_cache)

        # Positions should change somewhat.
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account1].get_amount(), 3_333.3333, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account2].get_amount(), 3_333.3333, delta=0.001)
        self.assertAlmostEqual(final_positions_by_fxpair[ILSUSD][account3].get_amount(), 3_333.3333, delta=0.001)


if __name__ == '__main__':
    unittest.main()
