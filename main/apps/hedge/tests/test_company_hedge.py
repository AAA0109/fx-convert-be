import unittest
from typing import Optional, Dict

import numpy as np
import pandas as pd
from django.test import testcases
from hdlib.Core.AccountInterface import BasicAccount, AccountInterface
from hdlib.Core.FxPair import FxPair
from hdlib.DataProvider.Fx.FxCorrelations import FxCorrelations
from hdlib.DataProvider.Fx.FxSpotVols import FxSpotVols
from hdlib.Hedge.Fx.HedgeAccount import HedgeAccountSettings, HedgeMethod, CashExposures, CashExposures_Cached

from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import FxMarketConverter

from hdlib.Core.CompanyInterface import BasicCompany, CompanyInterface

from hdlib.Core.Currency import USD, EUR, GBP
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.CashPnLAccount import CashPnLAccountHistoryProvider, CashPnLAccount
from hdlib.Hedge.Fx.HedgeCostProvider import HedgeCostProvider_Const
from hdlib.Instrument.CashFlow import CashFlow
from hdlib.TermStructures.ForwardCurve import FlatForwardCurve
from hdlib.Universe.Asset.FxAsset import FxAsset
from hdlib.Universe.FX.FxAssets import FxAssets
from hdlib.Universe.FX.FxUniverse import FxUniverse
from hdlib.Universe.Universe import Universe
from main.apps.hedge.calculators.company_hedge import CompanyHedgeCalculator, AccountPositionsProviderStored, \
    CompanyHedgeCallback

# Note - this is now in HDlib, but I don't want to update the version for just this item.
#  Pick it up later (will be in version 0.1.39).
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange


class CashPnLAccountHistoryProvider_Empty(CashPnLAccountHistoryProvider):
    """ A Cash PnL account history provider that doesn't do anything. """

    def get_account_state(self,
                          date: Date = None,
                          roll_down: bool = True,
                          universe: Optional[Universe] = None) -> CashPnLAccount:
        """ If Date is None, supply the first recorded state available """
        return CashPnLAccount(date=date)

    def get_first_date(self) -> Optional[Date]:
        """ Get first date of recorded history, if available, else None """
        return None


class TestingCompanyHedgeCallback(CompanyHedgeCallback):
    """ Callback that stores what the results of the account and aggregated changes were."""

    def __init__(self):
        self.live_changes = None
        self.demo_changes = None
        self.agg_live_changes = None
        self.agg_demo_changes = None

    def notify_account_position_changes(self,
                                        live_changes: Dict[AccountInterface, PositionChange],
                                        demo_changes: Dict[AccountInterface, PositionChange]):
        self.live_changes = live_changes
        self.demo_changes = demo_changes

    def notify_aggregated_changes(self, company: CompanyInterface, agg_live_changes: PositionChange,
                                  agg_demo_changes: PositionChange):
        self.agg_live_changes = agg_live_changes
        self.agg_demo_changes = agg_demo_changes

    def apply_liquidity_changes(self,
                                live_account_exposures: Dict[FxPair, Dict[AccountInterface, float]],
                                demo_account_exposures: Dict[FxPair, Dict[AccountInterface, float]],
                                live_liquidity_changes: Dict[FxPair, float],
                                demo_liquidity_changes: Dict[FxPair, float],
                                ):
        ...


# Create some FX pairs

EurUsd = FxPair(EUR, USD)
GbpUsd = FxPair(GBP, USD)

# Some accounts and companies for testing
company = BasicCompany("ACME", domestic=USD)
account = BasicAccount(company=company, name="Low risk")


def make_universe(ref_date, correlations):
    # ===================================================
    #  Create a Universe - this is the hardest part.
    # ===================================================

    fx_assets = FxAssets(ref_date=ref_date)
    fx_assets.add_asset(FxAsset(fx_pair=EurUsd, fwd_curve=FlatForwardCurve(F0=1.21, ref_date=ref_date)))
    fx_assets.add_asset(FxAsset(fx_pair=GbpUsd, fwd_curve=FlatForwardCurve(F0=1.12, ref_date=ref_date)))
    fx_vols = FxSpotVols(ref_date=ref_date, vols={EurUsd.name: 0.071, GbpUsd.name: 0.0632})

    pair_names = [EurUsd.name, GbpUsd.name]
    corr = pd.DataFrame(index=pair_names, columns=pair_names, dtype=float)
    for i in range(len(correlations)):
        for j in range(len(correlations[i])):
            rho = correlations[i][j]
            if i == j and rho != 1:
                raise ValueError("diagonal correlation must be 1.0")
            corr.iloc[i, j] = rho
    fx_corrs = FxCorrelations(ref_date=ref_date, instant_corr=corr)

    fx_universe = FxUniverse(ref_date=ref_date, fx_assets=fx_assets, fx_vols=fx_vols, fx_corrs=fx_corrs)
    universe = Universe(ref_date=ref_date, fx_universe=fx_universe)
    return universe


def create_setup(ref_date, cashflows, account_positions, universe, hedge_method, cost_provider=None):
    account_settings = HedgeAccountSettings(account=account,
                                            margin_budget=np.inf,
                                            method=hedge_method)
    exposures = CashExposures_Cached(date=ref_date,
                                     cashflows=cashflows,
                                     settings=account_settings)

    account_data = {account_settings: (exposures, exposures, CashPnLAccountHistoryProvider_Empty())}

    cost_provider = HedgeCostProvider_Const(fx_pairs=[EurUsd, GbpUsd]) if cost_provider is None else cost_provider
    market_converter = FxMarketConverter(traded_pairs={EurUsd: 1000, GbpUsd: 500})

    # Make up the current positions
    positions_provider = AccountPositionsProviderStored(fxspot_positions=account_positions)

    # ===================================================
    #  Create and run the hedger.
    # ===================================================

    results = TestingCompanyHedgeCallback()
    hedger = CompanyHedgeCalculator(company=company,
                                    account_data=account_data,
                                    cost_provider=cost_provider,
                                    market_converter=market_converter,
                                    universe=universe,
                                    callback=results)
    hedger.hedge_company(positions_provider=positions_provider)

    return results


class CompanyHedgeCalculatorTest(testcases.TestCase):
    def test_compute_basic_hedge(self):
        ref_date = Date.from_int(2020_01_01)

        cashflows = {
            EUR: [CashFlow(amount=10000, pay_date=ref_date + 7, currency=EUR)]
        }
        positions = {account: {EurUsd: 1000, GbpUsd: 5000}}
        universe = make_universe(ref_date=ref_date, correlations=[[1.00, 0.82], [0.82, 1.00]])

        results = create_setup(ref_date=ref_date, cashflows=cashflows, account_positions=positions,
                               universe=universe, hedge_method=HedgeMethod.PERFECT)

        self.assertEqual(results.agg_live_changes.new_positions[EurUsd], -10000)
        self.assertEqual(results.agg_live_changes.new_positions.get(GbpUsd, 0), 0)

    # noinspection DuplicatedCode
    def test_compute_basic_hedge2(self):
        """
        Even though there are strong correlations, a 'perfect' hedge will just take offsetting positions in each
        currency, as opposed to a min var hedge, which will allow some of the vols from the two assets to cancel.
        """
        ref_date = Date.from_int(2020_01_01)

        cashflows = {
            EUR: [CashFlow(amount=10000, pay_date=ref_date + 7, currency=EUR)],
            GBP: [CashFlow(amount=-10000, pay_date=ref_date + 7, currency=GBP)]
        }
        positions = {account: {EurUsd: 0, GbpUsd: 0}}
        universe = make_universe(ref_date=ref_date, correlations=[[1.00, 0.5], [0.5, 1.00]])

        results = create_setup(ref_date=ref_date, cashflows=cashflows, account_positions=positions,
                               universe=universe, hedge_method=HedgeMethod.PERFECT)

        self.assertEqual(results.agg_live_changes.new_positions[EurUsd], -10000)
        self.assertEqual(results.agg_live_changes.new_positions[GbpUsd], 10000)

    # noinspection DuplicatedCode
    def test_compute_minvar_nocosts(self):
        """
        Unless there are costs, there is no reason for the minvar optimizer not to take a perfectly offsetting
        position.
        """
        ref_date = Date.from_int(2020_01_01)

        cashflows = {
            EUR: [CashFlow(amount=10000, pay_date=ref_date + 7, currency=EUR)],
            GBP: [CashFlow(amount=-10000, pay_date=ref_date + 7, currency=GBP)]
        }
        positions = {account: {EurUsd: 0, GbpUsd: 0}}
        universe = make_universe(ref_date=ref_date, correlations=[[1.00, 0.5], [0.5, 1.00]])

        results = create_setup(ref_date=ref_date, cashflows=cashflows, account_positions=positions,
                               universe=universe, hedge_method=HedgeMethod.MIN_VAR)

        self.assertEqual(results.agg_live_changes.new_positions[EurUsd], -10000)
        self.assertEqual(results.agg_live_changes.new_positions[GbpUsd], 10000)

    # noinspection DuplicatedCode
    def test_compute_minvar_costs(self):
        """
        If there are costs to trading / holding positions, the min var should try to take advantage of offsetting.
        """
        ref_date = Date.from_int(2020_01_01)

        cashflows = {
            EUR: [CashFlow(amount=10000, pay_date=ref_date + 7, currency=EUR)],
            GBP: [CashFlow(amount=-10000, pay_date=ref_date + 7, currency=GBP)]
        }
        positions = {account: {EurUsd: 0, GbpUsd: 0}}
        universe = make_universe(ref_date=ref_date, correlations=[[1.00, 0.5], [0.5, 1.00]])

        cost_provider = HedgeCostProvider_Const(fx_pairs=[EurUsd, GbpUsd], roll_rates_long=[0.10, 0.10])

        results = create_setup(ref_date=ref_date, cashflows=cashflows, account_positions=positions,
                               universe=universe, hedge_method=HedgeMethod.MIN_VAR, cost_provider=cost_provider)

        self.assertAlmostEqual(round(results.agg_live_changes.new_positions[EurUsd], 2), -9772.39, places=1)
        self.assertAlmostEqual(round(results.agg_live_changes.new_positions[GbpUsd], 2), 9861.86, places=1)


if __name__ == '__main__':
    unittest.main()
