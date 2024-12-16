from django.test import TestCase

from main.apps.pricing.services.fee.product.autopilot.formula import AutopilotPricing
from main.apps.pricing.services.fee.product.parachute.formula import ParachutePricing


class TestAutopilotPricing(TestCase):

    def test_autopilot_pricing(self):
        autopilot = AutopilotPricing(
            annualized_volatility=0.07,
            settlement_days=365,
            target_eff=30,
            cashflow=1000000,
            size_category=1,
            risk_red=0.5,
            upside_on=True,
            downside_on=True,
            upside=0.01,
            downside=0.05
        )
        self.assertAlmostEqual(autopilot.cost, 5124.392723127396)

    def test_parachute_pricing(self):
        autopilot = ParachutePricing(
            annualized_volatility=0.07,
            settlement_days=365,
            target_eff=25,
            cashflow=1000000,
            size_category=2,
            safeguard=True,
            max_loss=0.05
        )
        self.assertAlmostEqual(autopilot.cost, 6388.136419987019)
