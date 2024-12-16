from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Company
from main.apps.hedge.api.service.whatif.base import BaseWhatIf
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.services.forward_cost_service import FxForwardCostCalculatorImpl
from main.apps.pricing.services.fee.product.autopilot.calculator import AutopilotCalculator, AutopilotStrategyConfig
from main.apps.pricing.services.fee.product.pricing_strategy import Cashflow as PricingCashFlow, OutputPrice


class AutopilotWhatIf(BaseWhatIf):
    def _get_hedge_metrics(self, fwd: DraftFxForwardPosition, ref_date: Date, fee: OutputPrice):
        cashflows = fwd.to_cashflows(ref_date=ref_date, base_only=True)
        upper_max_percent = self._get_upper_max_percent(fwd=fwd, ref_date=ref_date, cashflows=cashflows)
        risk_reduction = fwd.risk_reduction
        max_loss_threshold = 0
        safeguard_target = 0
        cashflows_amount = 0
        hedge_efficiency_ratio = None

        for cashflow in cashflows:
            cashflows_amount += abs(cashflow.amount)

        if fwd.account:
            if hasattr(fwd.account, 'autopilot_data'):
                autopilot_data = fwd.account.autopilot_data
                if autopilot_data:
                    max_loss_threshold = autopilot_data.lower_limit
                    safeguard_target = autopilot_data.upper_limit

        potential_loss_mitigated = risk_reduction * upper_max_percent

        if max_loss_threshold > 0:
            potential_loss_mitigated = risk_reduction * upper_max_percent + (
                (1 - risk_reduction) * (upper_max_percent - max_loss_threshold)
            )

        upside_preservation = upper_max_percent if safeguard_target == 0 else safeguard_target

        if fee.cost > 0:
            hedge_efficiency_ratio = potential_loss_mitigated / fee.cost

        return {
            "potential_loss_mitigated": potential_loss_mitigated,
            "upside_preservation": upside_preservation,
            "hedge_efficiency_ratio": hedge_efficiency_ratio
        }

    def _get_pangea_fees(self, fwd: DraftFxForwardPosition, ref_date: Date):
        cashflows = fwd.to_cashflows(ref_date=ref_date, base_only=True)
        _cashflows = []
        for cashflow in cashflows:
            _cashflows.append(
                PricingCashFlow(
                    value_date=Date.from_datetime_date(cashflow.date),
                    from_currency=cashflow.currency.mnemonic,
                    to_currency=fwd.company.currency.mnemonic,
                    from_amount=cashflow.amount
                )
            )

        risk_reduction = 1
        upper_limit = 0
        lower_limit = 0

        if fwd.account:
            if hasattr(fwd.account, 'autopilot_data'):
                autopilot_data = fwd.account.autopilot_data
                risk_reduction = fwd.risk_reduction
                if autopilot_data:
                    lower_limit = autopilot_data.lower_limit
                    upper_limit = autopilot_data.upper_limit

        strategy_config = AutopilotStrategyConfig(
            strategy='autopilot',
            risk_reduction=risk_reduction,
            upper_limit=upper_limit,
            lower_limit=lower_limit
        )
        pricing = AutopilotCalculator().get_pricing_for_strategy(
            cashflows=_cashflows,
            strategy_config=strategy_config,
            size=fwd.company.estimated_aum
        )
        return pricing

    def _get_broker_costs(self, fwd: DraftFxForwardPosition, ref_date: Date, company: Company, cache: SpotFxCache):
        notional = fwd.cashflow_notional(ref_date=ref_date, currency=company.currency,
                                         spot_fx_cache=cache)

        # Calculate Min Cost
        min_fx_fwd_cost = FxForwardCostCalculatorImpl(fx_quote_servie=self.fx_quote_service, spot_fx_cache=cache)
        min_fx_fwd_cost.add_forward(ref_date=ref_date, forward=fwd)
        min_cost = min_fx_fwd_cost.costs()
        if len(min_cost) != 1:
            raise ValueError("Expected exactly one min broker cost")
        min_cost = list(min_cost.values())[0]

        # this is the aggregated broker costs in company native currency
        min_broker_cost = min_fx_fwd_cost.broker_cost_in(company.currency, spot_fx_cache=cache)
        # we need to convert the broker cost into a percentage of the notional amount of the cashflow in USD
        min_broker_cost_bps = abs(min_broker_cost / notional) * 10000.0
        min_broker_cost_percent = min_broker_cost_bps / 100.0

        min_cost_dict = {
            "rate": min_cost,
            "percentage": min_broker_cost_percent,
            "bps": min_broker_cost_bps,
            "cost": min_broker_cost
        }

        # Calculate Max Cost
        max_fx_fwd_cost = FxForwardCostCalculatorImpl(fx_quote_servie=self.fx_quote_service, spot_fx_cache=cache)
        max_fx_fwd_cost.add_forward(ref_date=ref_date, forward=fwd, risk_reduction=1.0)
        max_cost = max_fx_fwd_cost.costs()
        if len(max_cost) != 1:
            raise ValueError("Expected exactly on max broker cost")
        max_cost = list(max_cost.values())[0]
        max_broker_cost = max_fx_fwd_cost.broker_cost_in(company.currency, spot_fx_cache=cache)
        max_broker_cost_bps = abs(max_broker_cost / notional) * 10000.0
        max_broker_cost_percent = max_broker_cost_bps / 100.0

        max_cost_dict = {
            "rate": max_cost,
            "percentage": max_broker_cost_percent,
            "bps": max_broker_cost_bps,
            "cost": max_broker_cost
        }
        return min_cost_dict, max_cost_dict
