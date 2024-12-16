import os
import sys


def autopilot_single_cashflows():
    autopilot = AutopilotPricing(
        annualized_volatility=0.07,
        settlement_days=365,
        target_eff=30,
        cashflow=1000000,
        size_category=1,
        risk_red=1,
        upside_on=True,
        downside_on=True,
        upside=0.01,
        downside=0.05
    )

    print("base_price: ", autopilot.base_price)
    print("risk_reduction:", autopilot.risk_reduction)
    print("size_of_client:", autopilot.size_of_client)
    print("subtotal:", autopilot.subtotal)
    print("upper: ", autopilot.upper)
    print("lower:", autopilot.lower)
    print("total_cost:", autopilot.total_cost)
    print("cost:", autopilot.cost)


def parachute_single_cashflows():
    parachute = ParachutePricing(
        annualized_volatility=0.0843,
        settlement_days=365,
        target_eff=25,
        cashflow=1000000,
        size_category=1,
        safeguard=True,
        max_loss=-0.05
    )

    print("base_price: ", parachute.base_price)
    print("risk_reduction:", parachute.risk_reduction)
    print("size_of_client:", parachute.size_of_client)
    print("subtotal:", parachute.subtotal)
    print("upper: ", parachute.upper)
    print("lower:", parachute.lower)
    print("total_cost:", parachute.total_cost)
    print("cost:", parachute.cost)


if __name__ == "__main__":
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
    import django

    django.setup()
    from main.apps.pricing.services.fee.product.autopilot.formula import AutopilotPricing
    from main.apps.pricing.services.fee.product.parachute.formula import ParachutePricing

    autopilot_single_cashflows()
    parachute_single_cashflows()
