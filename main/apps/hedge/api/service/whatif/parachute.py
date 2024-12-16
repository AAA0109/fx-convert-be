from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Company
from main.apps.hedge.api.service.whatif.base import BaseWhatIf
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.services.forward_cost_service import FxForwardCostCalculatorImpl
from main.apps.pricing.services.fee.product.parachute.calculator import ParachuteStrategyConfig, ParachuteCalculator
from main.apps.pricing.services.fee.product.pricing_strategy import Cashflow as PricingCashFlow, OutputPrice


class ParachuteWhatIf(BaseWhatIf):
    def _get_hedge_metrics(self, fwd: DraftFxForwardPosition, ref_date: Date, fee: OutputPrice):
        cashflows = fwd.to_cashflows(ref_date=ref_date, base_only=True)
        upper_max_percent = self._get_upper_max_percent(fwd=fwd, ref_date=ref_date, cashflows=cashflows)
        max_loss_threshold = 0
        cashflows_amount = 0
        hedge_efficiency_ratio = None
        return_risk_ratio = None

        for cashflow in cashflows:
            cashflows_amount += abs(cashflow.amount)

        if fwd.account:
            if hasattr(fwd.account, 'parachute_data'):
                parachute_data = fwd.account.parachute_data
                if parachute_data:
                    max_loss_threshold = parachute_data.lower_limit

        potential_loss_mitigated = upper_max_percent - max_loss_threshold
        if max_loss_threshold > 0:
            return_risk_ratio = upper_max_percent / abs(max_loss_threshold)

        if fee.cost > 0:
            hedge_efficiency_ratio = potential_loss_mitigated / fee.cost

        return {
            "potential_loss_mitigated": potential_loss_mitigated,
            "return_risk_ratio": return_risk_ratio,
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

        safeguard = False
        lower_limit = 0

        if fwd.account:
            if hasattr(fwd.account, 'parachute_data'):
                parachute_data = fwd.account.parachute_data
                if parachute_data:
                    lower_limit = parachute_data.lower_limit
                    safeguard = True if parachute_data.floating_pnl_fraction > 0 else False

        strategy_config = ParachuteStrategyConfig(
            strategy='parachute',
            lower_limit=lower_limit,
            safeguard=safeguard
        )
        pricing = ParachuteCalculator().get_pricing_for_strategy(
            cashflows=_cashflows,
            strategy_config=strategy_config,
            size=fwd.company.estimated_aum
        )
        return pricing

    def _get_broker_costs(self, fwd: DraftFxForwardPosition, ref_date: Date, company: Company, cache: SpotFxCache):
        notional = fwd.cashflow_notional(ref_date=ref_date, currency=company.currency,
                                         spot_fx_cache=cache)
        # Calculate Max Cost
        fx_fwd_cost = FxForwardCostCalculatorImpl(fx_quote_servie=self.fx_quote_service, spot_fx_cache=cache)
        fx_fwd_cost.add_forward(ref_date=ref_date, forward=fwd, risk_reduction=1.0)
        cost = fx_fwd_cost.costs()
        if len(cost) != 1:
            raise ValueError("Expected exactly on max broker cost")
        cost = list(cost.values())[0]
        broker_cost = fx_fwd_cost.broker_cost_in(company.currency, spot_fx_cache=cache)
        broker_cost_bps = abs(broker_cost / notional) * 10000.0
        broker_cost_percent = broker_cost_bps / 100.0

        min_cost_dict = {
            "rate": cost,
            "percentage": 0,
            "bps": 0,
            "cost": 0
        }
        max_cost_dict = {
            "rate": cost,
            "percentage": broker_cost_percent,
            "bps": broker_cost_bps,
            "cost": broker_cost
        }
        return min_cost_dict, max_cost_dict
