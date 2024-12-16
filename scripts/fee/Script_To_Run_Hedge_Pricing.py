import os
import sys
from typing import Union, List

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
    import django

    django.setup()
    from main.apps.pricing.services.fee.product.autopilot.calculator import AutopilotCalculator, AutopilotStrategyConfig
    from main.apps.pricing.services.fee.product.parachute.calculator import ParachuteCalculator, ParachuteStrategyConfig
    from main.apps.pricing.services.fee.product.pricing_strategy import Cashflow
    from scripts.fee.helper import get_sample_cashflows
    from main.apps.account.models.company import Company


    def recurring_cashflows(
        cashflows: List[Cashflow],
        strategy_config: Union[AutopilotStrategyConfig, ParachuteStrategyConfig],
        size: Company.EstimatedAumType
    ):
        if strategy_config.strategy == "autopilot":
            output_price = AutopilotCalculator().get_pricing_for_strategy(
                cashflows=cashflows,
                strategy_config=strategy_config,
                size=size
            )
        elif strategy_config.strategy == "parachute":
            output_price = ParachuteCalculator().get_pricing_for_strategy(
                cashflows=cashflows,
                strategy_config=strategy_config,
                size=size
            )
        else:
            raise ValueError("Invalid strategy")

        print("======== strategy: ", strategy_config.strategy, "=============")
        print("cost: ", output_price.cost)
        print("bps: ", output_price.bps)
        print("percentage: ", output_price.percentage)
        print(" ")


    cashflows = get_sample_cashflows("USD", "HUF")

    strategy_config = AutopilotStrategyConfig(
        strategy="autopilot",
        risk_reduction=0.5,
        upper_limit=0,
        lower_limit=0
    )
    recurring_cashflows(cashflows, strategy_config, Company.EstimatedAumType.AUM_UNDER_10M)

    strategy_config = ParachuteStrategyConfig(
        strategy="parachute",
        safeguard=False,
        lower_limit=0.085
    )
    recurring_cashflows(cashflows, strategy_config, Company.EstimatedAumType.AUM_UNDER_10M)
