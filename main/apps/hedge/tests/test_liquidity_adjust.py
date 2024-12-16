import unittest

import numpy as np
from django.test import TestCase

from typing import Dict

from hdlib.Core.CompanyInterface import BasicCompany

from hdlib.Core.AccountInterface import BasicAccount

from hdlib.Core.Currency import Currency, USD, EUR, GBP, JPY, ILS
from hdlib.Core.FxPair import FxPair
from main.apps.hedge.calculators.liquidity_adjust import get_liquidity_adjusted_positions
from main.apps.hedge.calculators.reconciliation import ReconciliationCalculator
from main.apps.hedge.support.account_hedge_interfaces import BasicAccountHedgeRequest
from main.apps.hedge.support.fx_fill_summary import FxFillSummary
from main.apps.hedge.support.fxposition_interface import BasicFxPosition
from main.apps.hedge.support.reconciliation_data import ReconciliationData


class LiquidityAdjustTest(TestCase):
    # noinspection DuplicatedCode
    def test__liquidity_adjust__example_case(self):
        """
        Example:
                    Total Exposure  |  Fx Position  |   Remaining
        ---------------------------------------------------------------
        Account A:   +130,000       |   -100,000    |   +30,000
        Account B:    -50,000       |   10,000      |   -40,000
        Account C:    -70,000       |   20,000      |   -50,000
        ---------------------------------------------------------------
        Net Exposure: +10,000
        Net Requested Hedge: -70,000
        Liquidity: -60,000

        Liquidity absorption: -60,000

        Remaining exposure from Account A: None, since sign(Remaining exposure A) != sign(Liquidity absorption)
        Remaining exposure from Account B: -40,000
        Remaining exposure from Account B: -50,000
        Total: -90,000

        -60,000 / -90,000 = 0.666 or 2/3 ==> Fraction to adjust accounts.

        Adjustment to Account A: None, since sign(Remaining exposure A) != sign(Liquidity absorption)
        Adjustment to Account B: -(-40,000 * 2/3) = 26,666.666
        Adjustment to Account C: -(-50,000 * 2/3) = 33,333.333

        Final Fx Position for Account A: -100,000
        Final Fx Position for Account B: +36,666
        Final Fx Position for Account C: +53,333
        """

        EURUSD = FxPair(base=EUR, quote=USD)

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account_A = BasicAccount(name="Account A", company=company)
        account_B = BasicAccount(name="Account B", company=company)
        account_C = BasicAccount(name="Account C", company=company)

        account_exposures = {EURUSD: {account_A: 130_000,
                                      account_B: -50_000,
                                      account_C: -70_000
                                      }}

        desired_positions = {EURUSD: {account_A: -100_000,
                                      account_B: 10_000,
                                      account_C: 20_000
                                      }}

        liquidity_changes = {EURUSD: -60_000}

        adjusted_positions = get_liquidity_adjusted_positions(account_exposures=account_exposures,
                                                              desired_positions=desired_positions,
                                                              liquidity_changes=liquidity_changes)

        self.assertAlmostEqual(adjusted_positions.get(EURUSD, {}).get(account_A, None), -100_000, delta=0.01)
        self.assertAlmostEqual(adjusted_positions.get(EURUSD, {}).get(account_B, None), 36_666.666, delta=0.01)
        self.assertAlmostEqual(adjusted_positions.get(EURUSD, {}).get(account_C, None), 53_333.333, delta=0.01)

    # noinspection DuplicatedCode
    def test__liquidity_adjust__perfect_cancellation(self):
        """
        Example:
                    Total Exposure  |  Fx Position  |   Remaining
        ---------------------------------------------------------------
        Account A:   +100,000       |   -100,000    |         0
        Account B:   -100,000       |   50,000      |   -50,000
        ---------------------------------------------------------------
        Net Exposure: 0
        Net Requested Hedge: -50,000
        Liquidity: -50,000

        Liquidity absorption: -50,000

        Remaining exposure from Account A:       0
        Remaining exposure from Account B: -50,000
        Total: -50,000

        -50,000 / -50,000 = 1 ==> Fraction to adjust accounts.

        Adjustment to Account A: None, since sign(Remaining exposure A) != sign(Liquidity absorption)
        Adjustment to Account B: -50,000

        Final Fx Position for Account A: -100,000
        Final Fx Position for Account B: +100,000
        """

        EURUSD = FxPair(base=EUR, quote=USD)

        company = BasicCompany(name="TEST COMPANY", domestic=USD)
        account_A = BasicAccount(name="Account A", company=company)
        account_B = BasicAccount(name="Account B", company=company)

        account_exposures = {EURUSD: {account_A: 100_000,
                                      account_B: -100_000,
                                      }}

        desired_positions = {EURUSD: {account_A: -100_000,
                                      account_B: 50_000,
                                      }}

        liquidity_changes = {EURUSD: -50_000}

        adjusted_positions = get_liquidity_adjusted_positions(account_exposures=account_exposures,
                                                              desired_positions=desired_positions,
                                                              liquidity_changes=liquidity_changes)

        self.assertAlmostEqual(adjusted_positions.get(EURUSD, {}).get(account_A, None), -100_000, delta=0.01)
        self.assertAlmostEqual(adjusted_positions.get(EURUSD, {}).get(account_B, None), 100_000, delta=0.01)


if __name__ == '__main__':
    unittest.main()
