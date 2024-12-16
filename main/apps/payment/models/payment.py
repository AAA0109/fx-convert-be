import uuid
from datetime import date, datetime
from typing import List, Optional

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from main.apps.account.models.company import Company
from main.apps.account.models.user import User

from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.api.dataclasses.best_execution import FxSpotInfo
from main.apps.oems.backend.calendar_utils import get_fx_spot_info
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.models.ticket import Ticket


class ExecutionOptions(models.TextChoices):
        IMMEDIATE_SPOT = 'immediate_spot', _("Immediate Spot")
        IMMEDIATE_FORWARD = 'immediate_forward', _("Immediate Forward")
        IMMEDIATE_NDF = 'immediate_ndf', _("Immediate NDF")
        STRATEGIC_SPOT = 'strategic_spot', _("Strategic Spot")
        STRATEGIC_FORWARD = 'strategic_forward', _("Strategic Forward")
        STRATEGIC_NDF = 'strategic_ndf', _("Strategic Execution NDF")
        SCHEDULED_SPOT = 'scheduled_spot', _("Scheduled Spot")


class Payment(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        AWAITING_FUNDS = 'awaiting_funds', _("Awaiting Funds")
        BOOKED = 'booked', _("Booked")
        DELIVERED = 'delivered', _("Delivered")
        DRAFTING = 'drafting', _("Drafting")
        IN_TRANSIT = 'in_transit', _("In Transit")
        SCHEDULED = 'scheduled', _("Scheduled")
        WORKING = 'working', _("Working")
        CANCELED = 'canceled', _("Canceled")
        FAILED = 'failed', _("Failed")
        SETTLEMENT_ISSUE = 'settlement_issue', _("Settlement Issue")
        PENDAUTH = 'pend_auth', _("Pending Authorization")
        STRATEGIC_EXECUTION = 'strategic_execution', _("Strategic Ex")
        EXPIRED = 'expired', _("Expired")
        PENDING_APPROVAL = 'pending_approval', _("Pending Approval")
        TRADE_DESK = 'trade_desk', _("Trade Desk")
        PENDING_BENEFICIARY = 'pending_beneficiary', _("Pending Beneficiary")
        PAYMENT_ISSUE = 'payment_issue', _("Payment Issue")
        SETTLED = 'settled', _("Settled")
        APPROVED = "approved", _("Approved")

    OEMS_STATE_MAPPING = {
        INTERNAL_STATES.NEW: PaymentStatus.DRAFTING,
        INTERNAL_STATES.DRAFT: PaymentStatus.DRAFTING,
        INTERNAL_STATES.ACTIVE: PaymentStatus.WORKING,
        INTERNAL_STATES.PENDAUTH: PaymentStatus.PENDING_APPROVAL,
        INTERNAL_STATES.PENDMARGIN: PaymentStatus.AWAITING_FUNDS,
        INTERNAL_STATES.SCHEDULED: PaymentStatus.SCHEDULED,
        INTERNAL_STATES.WAITING: PaymentStatus.WORKING,
        INTERNAL_STATES.ACCEPTED: PaymentStatus.WORKING,
        INTERNAL_STATES.WORKING: PaymentStatus.WORKING,
        INTERNAL_STATES.PENDPAUSE: PaymentStatus.WORKING,
        INTERNAL_STATES.PENDRESUME: PaymentStatus.WORKING,
        INTERNAL_STATES.PAUSED: PaymentStatus.WORKING,
        INTERNAL_STATES.PENDCANCEL: PaymentStatus.WORKING,
        INTERNAL_STATES.CANCELED: PaymentStatus.CANCELED,
        INTERNAL_STATES.CANCELREJECT: PaymentStatus.BOOKED,
        INTERNAL_STATES.PTLCANCEL: PaymentStatus.BOOKED,
        INTERNAL_STATES.FILLED: PaymentStatus.BOOKED,
        INTERNAL_STATES.PARTIAL: PaymentStatus.BOOKED,
        INTERNAL_STATES.PENDSETTLE: PaymentStatus.BOOKED,
        INTERNAL_STATES.PENDBENE: PaymentStatus.PENDING_BENEFICIARY,
        INTERNAL_STATES.PENDFUNDS: PaymentStatus.AWAITING_FUNDS,
        INTERNAL_STATES.BOOKED: PaymentStatus.BOOKED,
        INTERNAL_STATES.PENDRECON: PaymentStatus.SETTLED,
        INTERNAL_STATES.DONE: PaymentStatus.SETTLED,
        INTERNAL_STATES.DONE_PENDSETTLE: PaymentStatus.SETTLED,
        INTERNAL_STATES.ERROR: PaymentStatus.PAYMENT_ISSUE,
        INTERNAL_STATES.FAILED: PaymentStatus.PAYMENT_ISSUE,
        INTERNAL_STATES.EXPIRED: PaymentStatus.PAYMENT_ISSUE,
        INTERNAL_STATES.PEND_RFQ: PaymentStatus.TRADE_DESK,
        INTERNAL_STATES.RFQ_DONE: PaymentStatus.WORKING,
        INTERNAL_STATES.MANUAL: PaymentStatus.WORKING,
        INTERNAL_STATES.BOOKING_FAILURE: PaymentStatus.PAYMENT_ISSUE,
        INTERNAL_STATES.SETTLE_FAIL: PaymentStatus.SETTLEMENT_ISSUE,
    }
    cashflow_generator = models.ForeignKey(CashFlowGenerator, on_delete=models.CASCADE, related_name="payment",
                                           null=False)

    # wallet or bank account id
    origin_account_id = models.CharField(max_length=50, null=True, blank=True)

    # delivery method
    origin_account_method = models.CharField(max_length=50, null=True, blank=True)

    # wallet id or beneficiary id
    destination_account_id = models.CharField(max_length=50, null=True, blank=True)

    # delivery method
    destination_account_method = models.CharField(max_length=50, null=True, blank=True)

    class PurposeOfPayment(models.TextChoices):
        PURCHASE_OF_GOODS = "PURCHASE OF GOOD(S)", _("Purchase of Good(s)")
        PURCHASE_PROFESSIONAL_SERVICE = "PURCHASE PROFESSIONAL SERVICE", _("Purchase of Professional Service(s)")
        PROFESSIONAL_FEES_PAYMENT = "PROFESSIONAL FEES PAYMENT", _(
            "Professional fees payment (i.e. legal, accountant)")
        PAYROLL_PERSONNEL_PAYMENT = "PAYROLL/PERSONNEL PAYMENT", _("Payroll/Personnel payment")
        PAYMENT_FOR_LOAN_OR_DEPOSIT = "PAYMENT FOR A LOAN OR DEPOSIT", _("Payment for a loan or deposit")
        BILL_PAYMENT = "BILL PAYMENT", _("Bill payment (i.e. credit card, utility)")
        RESEARCH_AND_DEVELOPMENT = "RESEARCH AND DEVELOPMENT", _("Research and Development")
        BUSINESS_VENTURE = "BUSINESS VENTURE", _("Business venture (i.e. merger, acquisition)")
        INTERCOMPANY_PAYMENT = "INTERCOMPANY PAYMENT", _("Intercompany payment")
        CHARITABLE_DONATION = "CHARITABLE DONATION", _("Charitable donation")
        PURCHASE_OF_PROPERTY = "PURCHASE OF PROPERTY / REAL ESTATE", _("Purchase of property / real estate")
        ESTATE_SETTLEMENT = "ESTATE SETTLEMENT / INHERITANCE", _("Estate settlement / Inheritance")
        GOVERNMENT_RELATED_PAYMENT = "GOVERNMENT RELATED PAYMENT", _("Government related payment")
        INVESTMENT_RELATED_PAYMENT = "INVESTMENT RELATED PAYMENT", _("Investment related payment")
        FAMILY_ASSISTANCE = "PAYMENT,FAMILY ASSISTANCE", _("Payment,Family Assistance")
        MEDICAL_ASSISTANCE = "MEDICAL ASSISTANCE", _("Medical Assistance")
        MEDICAL_CLAIM_REIMBURSEMENT = "MEDICAL CLAIM REIMBURSEMENT", _("Medical Claim Reimbursement")
        REMITTANCE_FROM_ECOMMERCE = "REMITTANCE OF FUNDS FROM E-COMMERCE", _("Remittance of funds from e-commerce")
        IP_TRADEMARK_PATENT_WORK = "IP TRADEMARK PATENT WORK", _("IP Trademark Patent Work")
        TRAVEL_HOSPITALITY = "TRAVEL HOSPITALITY", _("Travel/Hospitality")
        PUBLISHER = "PUBLISHER", _("Publisher")

    purpose_of_payment = models.CharField(max_length=255, null=True, blank=True)

    payment_status = models.CharField(max_length=25, choices=PaymentStatus.choices, default=PaymentStatus.DRAFTING)

    fee_in_bps = models.IntegerField(null=True, blank=True, default=0)
    fee = models.FloatField(null=True, blank=True, default=0)

    payment_group = models.CharField(null=True, blank=True, max_length=100)

    class ExecutionTiming(models.TextChoices):
        IMMEDIATE = 'immediate', _("Immediate")
        STRATEGIC_EXECUTION = 'strategic_execution', _("Strategic Execution")
        SCHEDULED = 'scheduled', _("Scheduled Transaction")

    execution_timing = models.CharField(null=True, blank=True,max_length=25, choices=ExecutionTiming.choices)
    payment_ident = models.CharField(null=True, blank=True)
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    create_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_create_user",
                                    null=True, blank=True)
    auth_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_auth_user",
                                    null=True, blank=True)

    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)

    execution_option = models.CharField(null=True, blank=True, max_length=25, choices=ExecutionOptions.choices)

    @property
    def related_cashflows(self) -> List[SingleCashFlow]:
        return SingleCashFlow.objects.filter(generator=self.cashflow_generator).select_related('company',
                                                                                               'buy_currency',
                                                                                               'sell_currency',
                                                                                               'lock_side')

    def get_ticket_execution_strategy(self) -> str:
        if self.execution_timing == Payment.ExecutionTiming.STRATEGIC_EXECUTION:
            return Ticket.ExecutionStrategies.BESTX
        elif self.execution_timing == Payment.ExecutionTiming.SCHEDULED:
            return Ticket.ExecutionStrategies.BESTX
        return Ticket.ExecutionStrategies.MARKET

    def remove_tzinfo(self, date: datetime) -> datetime:
        if not date:
            return date
        try:
            new_date = date.replace(tzinfo=None)
            return new_date
        except Exception as e:
            return date

    def get_value_date(self) -> date:
        value_date = self.cashflow_generator.value_date
        if self.cashflow_generator.recurring == True or self.cashflow_generator.installment == True:
            cashflows = SingleCashFlow.objects.filter(generator=self.cashflow_generator)
            return cashflows[0].pay_date
        if value_date is None:
            return datetime.now().date()
        return value_date.date() if isinstance(value_date, datetime) else value_date

    def get_execution_strategy(self) -> str:
        now = datetime.now()
        cashflows = SingleCashFlow.objects.filter(generator=self.cashflow_generator)
        fx_pair = FxPair.get_pair_from_currency(base_currency=self.cashflow_generator.sell_currency,
                                             quote_currency=self.cashflow_generator.buy_currency)
        fx_spot_info = get_fx_spot_info(mkt=fx_pair.market, dt=now)
        fx_spot_info = FxSpotInfo(**fx_spot_info)
        is_spot = cashflows[0].pay_date.date() <= fx_spot_info.spot_value_date
        if self.execution_timing == Payment.ExecutionTiming.IMMEDIATE:
            return 'Immediate Spot FX' if is_spot else 'Immediate Forward FX'
        elif self.execution_timing == Payment.ExecutionTiming.STRATEGIC_EXECUTION:
            return 'Strategic Spot FX' if is_spot else 'Strategic Forward FX'
        elif self.execution_timing == Payment.ExecutionTiming.SCHEDULED:
            return 'Scheduled Spot FX' if is_spot else 'Scheduled Forward FX'
        return ''

    def get_amount(self, to_currency_format:bool=False) -> float:
        amount = 0
        if self.cashflow_generator.lock_side == self.cashflow_generator.sell_currency:
            cashflows = SingleCashFlow.objects.filter(generator=self.cashflow_generator)
            for cashflow in cashflows:
                amount += cashflow.amount
        if self.cashflow_generator.lock_side == self.cashflow_generator.buy_currency:
            cashflows = SingleCashFlow.objects.filter(generator=self.cashflow_generator)
            for cashflow in cashflows:
                amount += cashflow.cntr_amount
        if to_currency_format:
            return self.cashflow_generator.lock_side.mnemonic + " {:0,.2f}".format(amount)
        return amount

    def get_approvers(self) -> list[User]:
        approvers = []
        if self.cashflow_generator.approver_1 is not None:
            approvers.append(self.cashflow_generator.approver_1)
        if self.cashflow_generator.approver_2 is not None:
            approvers.append(self.cashflow_generator.approver_2)
        return approvers

    def get_payment_pair(self) -> Optional[FxPair]:
        pair = FxPair.get_pair_from_currency(base_currency=self.cashflow_generator.sell_currency,
                                        quote_currency=self.cashflow_generator.buy_currency)
        return pair

    @staticmethod
    def get_exec_timing_from_exec_option(exec_option:str) -> str:
        if exec_option in [ExecutionOptions.IMMEDIATE_SPOT, ExecutionOptions.IMMEDIATE_FORWARD,
                           ExecutionOptions.IMMEDIATE_NDF]:
            return Payment.ExecutionTiming.IMMEDIATE
        elif exec_option in [ExecutionOptions.STRATEGIC_SPOT, ExecutionOptions.STRATEGIC_FORWARD,
                             ExecutionOptions.STRATEGIC_NDF]:
            return Payment.ExecutionTiming.STRATEGIC_EXECUTION
        elif exec_option == ExecutionOptions.SCHEDULED_SPOT:
            return Payment.ExecutionTiming.SCHEDULED
        return None
