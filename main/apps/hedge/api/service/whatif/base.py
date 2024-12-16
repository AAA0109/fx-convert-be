from abc import ABC
from typing import List, Union

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import CashFlow, Company
from main.apps.billing.services.what_if import FeeWhatIfService
from main.apps.corpay.services.credit_utilization import CreditUtilizationService
from main.apps.pricing.services.fee.product.pricing_strategy import OutputPrice
from main.apps.hedge.api.serializers.whatif.parachute import ParachuteWhatIfResponseSerializer
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.api.serializers.whatif.autopilot import AutopilotWhatIfResponseSerializer
from main.apps.hedge.services.forward_cost_service import FxQuoteService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.risk_metric.services.cashflow_risk_provider import CashFlowRiskService
from main.apps.strategy.models.choices import Strategies


class BaseWhatIf(ABC):
    def __init__(self,
                 credit_utilization_service: CreditUtilizationService,
                 fx_quote_service: FxQuoteService,
                 fee_what_if: FeeWhatIfService,
                 fx_spot_provider: FxSpotProvider):
        self.credit_utilization_service = credit_utilization_service
        self.fx_quote_service = fx_quote_service
        self.fee_what_if = fee_what_if
        self.fx_spot_provider = fx_spot_provider

    def what_if(self, ref_date: Date, fx_forward: DraftFxForwardPosition, strategy: Strategies.values) -> Union[
        ParachuteWhatIfResponseSerializer,
        AutopilotWhatIfResponseSerializer
    ]:
        company = fx_forward.company
        corpaysettings = company.corpaysettings
        if not corpaysettings:
            raise ValueError("Company does not have corpay settings")
        cache = self.fx_spot_provider.get_spot_cache(time=ref_date)
        utilization = self.credit_utilization_service.get_credit_utilization(company)
        broker_cost_min, broker_cost_max = self._get_broker_costs(fwd=fx_forward, ref_date=ref_date, company=company,
                                                                  cache=cache)
        pangea_fee = self._get_pangea_fees(fwd=fx_forward, ref_date=ref_date)
        hedge_metrics = self._get_hedge_metrics(fx_forward, ref_date, pangea_fee)

        notional_in_base = abs(
            cache.convert_value(fx_forward.notional(), fx_forward.fxpair.base_currency, company.currency))

        credit_usage = {
            "available": utilization.available(),
            "required": notional_in_base,
        }
        rate = {
            "fwd_rate": broker_cost_min['rate'].forward_price,
            "spot_rate": broker_cost_min['rate'].spot,
            "fwd_points": broker_cost_min['rate'].market_points
        }
        fee = [
            {
                "fee_type": "broker_min",
                "percentage": broker_cost_min['percentage'],
                "bps": broker_cost_min['bps'],
                "cost": broker_cost_min['cost']
            },
            {
                "fee_type": "broker_max",
                "percentage": broker_cost_max['percentage'],
                "bps": broker_cost_max['bps'],
                "cost": broker_cost_max['cost']
            },
            {
                "fee_type": "pangea",
                "percentage": pangea_fee.percentage,
                "bps": pangea_fee.bps,
                "cost": pangea_fee.cost
            },
            {
                "fee_type": "total_min",
                "percentage": pangea_fee.percentage + broker_cost_min['percentage'],
                "bps": pangea_fee.bps + broker_cost_min['bps'],
                "cost": pangea_fee.cost + broker_cost_min['cost']
            },
            {
                "fee_type": "total_max",
                "percentage": pangea_fee.percentage + broker_cost_max['percentage'],
                "bps": pangea_fee.bps + broker_cost_max['bps'],
                "cost": pangea_fee.cost + broker_cost_max['cost']
            },
        ]

        response = {
            "credit_usage": credit_usage,
            "rate": rate,
            "fee": fee,
            "hedge_metric": hedge_metrics
        }
        if strategy == Strategies.PARACHUTE:
            return ParachuteWhatIfResponseSerializer(response)
        return AutopilotWhatIfResponseSerializer(response)

    def _get_cashflows_from_forward(self, cashflows: List[CashFlow]):
        _cashflows = {}
        for cashflow in cashflows:
            if cashflow.currency not in _cashflows:
                _cashflows.setdefault(cashflow.currency, [])
            _cashflows[cashflow.currency].append(
                CashFlow(
                    date=cashflow.date,
                    currency=cashflow.currency,
                    amount=cashflow.amount,
                    name=cashflow.name,
                    description=cashflow.description,
                    periodicity=cashflow.periodicity,
                    calendar=cashflow.calendar,
                    roll_convention=cashflow.roll_convention,
                    end_date=cashflow.end_date
                )
            )
        return _cashflows

    def _get_hedge_metrics(self, fwd: DraftFxForwardPosition, ref_date: Date, fee: OutputPrice):
        raise NotImplementedError

    def _get_pangea_fees(self, fwd: DraftFxForwardPosition, ref_date: Date):
        raise NotImplementedError

    def _get_broker_costs(self, fwd: DraftFxForwardPosition, ref_date: Date, company: Company, cache: SpotFxCache):
        raise NotImplementedError

    def _get_upper_max_percent(self, fwd: DraftFxForwardPosition, ref_date: Date, cashflows: List[CashFlow]):
        end_date = Date.from_datetime_date(cashflows[-1].date)
        risk_cone_cashflows = self._get_cashflows_from_forward(cashflows)
        cones = CashFlowRiskService().get_cashflow_risk_cones(
            cashflows=risk_cone_cashflows,
            do_std_dev_cones=True,
            domestic=fwd.company.currency,
            end_date=end_date,
            max_horizon=730,
            start_date=ref_date,
            std_dev_levels=[1, 2, 3],
            account=-1,
        )
        upper_max_percent = cones['upper_max_percents'][-1]
        return upper_max_percent
