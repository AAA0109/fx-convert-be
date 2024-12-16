import pytz
import logging
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional, Tuple
from main.apps.approval.services.approval import CompanyApprovalService
from main.apps.approval.services.limit import CompanyLimitService
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.spread import SpreadProvider
from main.apps.oems.api.dataclasses.best_execution import BestExecStatus, FxSpotInfo
from main.apps.oems.api.dataclasses.liquidity_insight import LiquidityStatus, MarketStatus
from main.apps.oems.backend.calendar_utils import get_fx_spot_info
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.services.currency_execution import CompanyCnyExecutionProvider
from main.apps.payment.models.payment import ExecutionOptions, Payment


logger = logging.getLogger(__name__)


class ExecutionOptionProvider:
    payment: Payment
    fx_pair: FxPair
    cashflows: List[SingleCashFlow]
    cashflow: SingleCashFlow
    now: datetime
    NY_TZ: pytz.tzinfo.DstTzInfo = pytz.timezone('America/New_York')
    UTC_TZ: pytz.tzinfo.DstTzInfo = pytz.timezone('UTC')

    def __init__(self, payment: Payment) -> None:
        self.payment = payment
        self.cashflows = list(SingleCashFlow.objects.filter(
            generator=payment.cashflow_generator))
        self.cashflows.sort(key=lambda cashflow: cashflow.pay_date)
        self.cashflow = self.cashflows[0]
        self.fx_pair = FxPair.get_pair_from_currency(
            base_currency=self.cashflow.sell_currency,
            quote_currency=self.cashflow.buy_currency
        )
        self.now = datetime.utcnow()

    def _get_liquidity_status(self, recommend:bool, market_status:Optional[str] = None) -> Optional[str]:
        """Get liquidity status from spread service."""
        spread_provider = SpreadProvider(fx_pair=self.fx_pair, ref_date=self.now)
        liquidity = spread_provider.get_liquidity_status(weekday=self.now.weekday(),
                                                         hour=self.now.hour, spread=None)
        if liquidity is None and market_status != MarketStatus.CLOSE.value:
            return LiquidityStatus.ACCEPTABLE.value if recommend else LiquidityStatus.POOR.value
        return liquidity

    def _is_spot(self, fx_spot_info: FxSpotInfo) -> bool:
        """Determine if the trade type is spot."""
        return self.cashflow.pay_date.date() <= fx_spot_info.spot_value_date

    def _get_fwd_rfq_type(self) -> Tuple[bool, str]:
        """Return 'NDF', 'Unsupported', or 'Supported' based on forward type."""
        cny_exec = CompanyCnyExecutionProvider(company=self.payment.company,
                                                fx_pair=self.payment.get_payment_pair().market)
        is_ndf, fwd_rfq_type = cny_exec.is_ndf()
        return is_ndf, fwd_rfq_type

    def _approvals_required(self) -> bool:
        """Return True if approvals are required based on cashflow configuration."""
        limit_service = CompanyLimitService(company=self.payment.company)
        discounted_amount, is_exceeding_limit = limit_service.validate_transaction_limit(
            currency=self.cashflow.lock_side,
            amount=self.cashflow.amount,
            value_date=self.cashflow.pay_date.date())
        approval_svc = CompanyApprovalService(company=self.payment.company)
        require_approval = approval_svc.is_transaction_require_approval(converted_amount=discounted_amount)
        return require_approval

    def _is_weekend(self, exec_status: BestExecStatus) -> bool:
        """Check if today date is a weekend."""
        ny_now = datetime.now(tz=self.NY_TZ)
        ny_weekday = ny_now.weekday()
        return exec_status.session == 'Weekend' or ny_weekday in [5, 6]

    def _determine_execution_options(self, liquidity_status: str, market_status: str,
                                    is_spot: bool, rfq_type: str, is_recurring_or_installment: bool,
                                    approval_required: bool) -> List[str]:
        """
        Determine executions options based on liquidity status, market status, spot status,
        rfq type, payment type and approval requirement status
        """
        if is_recurring_or_installment:
            return [ExecutionOptions.SCHEDULED_SPOT]
        # FwdUnsupported
        elif not is_spot and rfq_type == CnyExecution.RfqTypes.UNSUPPORTED:
            return [ExecutionOptions.SCHEDULED_SPOT]
        # Good/Open/Spot
        elif liquidity_status == LiquidityStatus.GOOD.value and \
            market_status == MarketStatus.OPEN.value and is_spot:
            if approval_required:
                return [ExecutionOptions.STRATEGIC_SPOT]
            return [ExecutionOptions.IMMEDIATE_SPOT]
        # NotGood/Open/Spot
        elif liquidity_status in [LiquidityStatus.ACCEPTABLE.value, LiquidityStatus.POOR.value] and \
            market_status == MarketStatus.OPEN.value and is_spot:
            if approval_required:
                return [ExecutionOptions.STRATEGIC_SPOT]
            return [ExecutionOptions.IMMEDIATE_SPOT, ExecutionOptions.STRATEGIC_SPOT]
        # Good/Open/FwdApi
        elif liquidity_status == LiquidityStatus.GOOD.value and \
            market_status == MarketStatus.OPEN.value and not is_spot and \
            rfq_type == CnyExecution.RfqTypes.API:
            if approval_required:
                return  [ExecutionOptions.STRATEGIC_FORWARD, ExecutionOptions.SCHEDULED_SPOT]
            return [ExecutionOptions.IMMEDIATE_FORWARD, ExecutionOptions.SCHEDULED_SPOT]
        # NotGood/Open/FwdApi
        elif liquidity_status in [LiquidityStatus.ACCEPTABLE.value, LiquidityStatus.POOR.value] and \
            market_status == MarketStatus.OPEN.value and not is_spot and \
            rfq_type == CnyExecution.RfqTypes.API:
            if approval_required:
                return  [ExecutionOptions.STRATEGIC_FORWARD, ExecutionOptions.SCHEDULED_SPOT]
            return [ExecutionOptions.IMMEDIATE_FORWARD, ExecutionOptions.STRATEGIC_FORWARD,
                    ExecutionOptions.SCHEDULED_SPOT]
        # Good/Open/FwdManual
        elif liquidity_status == LiquidityStatus.GOOD.value and \
            market_status == MarketStatus.OPEN.value and not is_spot and \
            rfq_type == CnyExecution.RfqTypes.MANUAL:
            if approval_required:
                return  [ExecutionOptions.STRATEGIC_NDF, ExecutionOptions.SCHEDULED_SPOT]
            return [ExecutionOptions.IMMEDIATE_NDF, ExecutionOptions.SCHEDULED_SPOT]
        # NotGood/Open/FwdManual
        elif liquidity_status in [LiquidityStatus.ACCEPTABLE.value, LiquidityStatus.POOR.value] and \
            market_status == MarketStatus.OPEN.value and not is_spot and \
            rfq_type == CnyExecution.RfqTypes.MANUAL:
            if approval_required:
                return  [ExecutionOptions.STRATEGIC_NDF, ExecutionOptions.SCHEDULED_SPOT]
            return [ExecutionOptions.IMMEDIATE_NDF, ExecutionOptions.STRATEGIC_NDF,
                    ExecutionOptions.SCHEDULED_SPOT]
        # None/Close/FwdApi
        elif liquidity_status is None and market_status == MarketStatus.CLOSE.value and \
            not is_spot and rfq_type == CnyExecution.RfqTypes.API:
            return [ExecutionOptions.STRATEGIC_FORWARD, ExecutionOptions.SCHEDULED_SPOT]
        # None/Close/FwdManual
        elif liquidity_status is None and market_status == MarketStatus.CLOSE.value and \
            not is_spot and rfq_type == CnyExecution.RfqTypes.MANUAL:
            return [ExecutionOptions.STRATEGIC_NDF, ExecutionOptions.SCHEDULED_SPOT]
        # None/Close/FwdUnsupported
        elif liquidity_status is None and market_status == MarketStatus.CLOSE.value and \
            not is_spot and rfq_type == CnyExecution.RfqTypes.UNSUPPORTED:
            return [ExecutionOptions.SCHEDULED_SPOT]
        # None/Close/Spot
        elif liquidity_status is None and \
            market_status == MarketStatus.CLOSE.value and is_spot:
            return [ExecutionOptions.STRATEGIC_SPOT]
        return []

    def __modify_best_ex_status(self, exec_status: BestExecStatus, execution_timing: str) -> BestExecStatus:
        """Modify best execution status for each option"""
        if execution_timing in [ExecutionOptions.IMMEDIATE_SPOT, ExecutionOptions.IMMEDIATE_FORWARD,
                                ExecutionOptions.IMMEDIATE_NDF]:
            return exec_status

        exec_status_copy = BestExecStatus(**asdict(exec_status))

        exec_status_copy.check_back = None
        exec_status_copy.execute_before = None
        exec_status_copy.recommend = None

        if execution_timing in [ExecutionOptions.STRATEGIC_SPOT, ExecutionOptions.STRATEGIC_FORWARD,
                                ExecutionOptions.STRATEGIC_NDF]:
            exec_status_copy.recommend = not exec_status.recommend

        return exec_status_copy

    def get_execution_options(self) -> dict:
        """Populate executions options for the given payment"""
        fx_spot_info = FxSpotInfo(**get_fx_spot_info(self.fx_pair.market, dt=self.now))
        exec_status = BestExecStatus(**get_best_execution_status(self.fx_pair.market, ref_date=self.now))

        is_weekend = self._is_weekend(exec_status=exec_status)
        market_status = MarketStatus.CLOSE.value if is_weekend else MarketStatus.OPEN.value
        liquidity_status = self._get_liquidity_status(recommend=exec_status.recommend,
                                                       market_status=market_status)
        is_spot = self._is_spot(fx_spot_info=fx_spot_info)
        is_ndf, rfq_type = self._get_fwd_rfq_type()
        is_recurring_or_installment = self.payment.cashflow_generator.installment or \
            self.payment.cashflow_generator.recurring
        approval_required = self._approvals_required()

        execution_options = self._determine_execution_options(
            liquidity_status=liquidity_status,
            market_status=market_status,
            is_spot=is_spot,
            rfq_type=rfq_type,
            is_recurring_or_installment=is_recurring_or_installment,
            approval_required=approval_required
        )

        options = []
        for timing in execution_options:
            exec_status_copy = self.__modify_best_ex_status(exec_status=exec_status, execution_timing=timing)
            label = ' '.join([char.capitalize() for char in timing.split('_')])
            exec_status_copy.label = label
            exec_status_copy.value = timing
            options.append(exec_status_copy)

        return {
            'execution_timings': options,
            'execution_data': {
                'liquidity_insight': {
                    'liquidity': liquidity_status
                },
                'spot_value_date': fx_spot_info.spot_value_date
            }
        }
