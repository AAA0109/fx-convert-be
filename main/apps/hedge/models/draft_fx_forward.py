import logging
import uuid
from typing import Optional, Iterable, List

from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as __
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import (
    CashFlow,
    Company,
    iter_active_cashflows,
    DraftCashFlow,
    InstallmentCashflow,
    Account,
)
from main.apps.corpay.models import DestinationAccountType
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.hedge.models import HedgeSettings
from main.apps.strategy.models.choices import Strategies

logger = logging.getLogger(__name__)


class DraftFxForwardPosition(TimeStampedModel):
    class Meta:
        verbose_name_plural = "Draft FX Forward Positions"

    class Status(models.TextChoices):
        DRAFT = "draft", __("DRAFT")
        PENDING_ACTIVATION = "pending_activation", __("PENDING ACTIVATION")
        ACTIVE = "active", __("ACTIVE")

    status = models.CharField(max_length=24, default=Status.DRAFT, choices=Status.choices)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    risk_reduction = models.FloatField(null=False)

    # Where to pull funds from during settlement
    origin_account = models.CharField(null=True, max_length=60, blank=True)

    # Where to send funds to during settlement
    destination_account = models.CharField(null=True, max_length=60, blank=True)

    # Destination account type
    destination_account_type = models.CharField(choices=DestinationAccountType.choices, max_length=1, null=True,
                                                blank=True)

    # What account to use for cash settlement
    cash_settle_account = models.CharField(null=True, max_length=60, blank=True)

    # Where to pull funds from in case of insufficient balance in origin_account
    funding_account = models.CharField(null=True, max_length=60, blank=True)

    # Flag for cash settlement
    is_cash_settle = models.BooleanField(default=False)

    # Purpose of Payment
    purpose_of_payment = models.CharField(null=True, max_length=60, blank=True)

    estimated_fx_forward_price = models.FloatField(null=True, blank=True)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, null=True, blank=True)
    draft_cashflow = models.ForeignKey(DraftCashFlow, on_delete=models.SET_NULL, null=True, blank=True)
    installment = models.ForeignKey(InstallmentCashflow, on_delete=models.CASCADE, null=True, blank=True)

    @property
    def account(self):
        if self.cashflow is not None:
            return self.cashflow.account
        if self.draft_cashflow is not None:
            return self.draft_cashflow.account
        if self.installment is not None:
            if self.installment.cashflow_set.count():
                return self.installment.cashflow_set.first().account
            if self.installment.draftcashflow_set.count():
                return self.installment.draftcashflow_set.first().account
        return None

    @property
    def strategy(self):
        if hasattr(self.account, 'parachute_data'):
            return Strategies.PARACHUTE
        if hasattr(self.account, 'autopilot_data') or self.risk_reduction is not None:
            return Strategies.AUTOPILOT

    def notionals(self, ref_date: Date) -> Iterable[float]:
        notionals = []

        cashflows = self.get_cashflows()
        for cf in iter_active_cashflows(cfs=cashflows, ref_date=ref_date):
            notionals.append(-cf.amount * self.risk_reduction)
        return notionals

    def notionals_in_company_currency(self, ref_date: Date, spot_fx_cache: SpotFxCache,
                                      risk_reduction: Optional[float] = None) -> Iterable[float]:
        cny = self.company.currency
        notionals = []

        cashflows = self.get_cashflows()
        for cf in iter_active_cashflows(cfs=cashflows, ref_date=ref_date):
            amount = round(spot_fx_cache.convert_value(-cf.amount, cf.currency, cny), 5)
            if risk_reduction is not None:
                notionals.append(amount * risk_reduction)
            else:
                notionals.append(amount * self.risk_reduction)

        return notionals

    @property
    def max_horizon(self):
        corpaysettings = self.company.corpaysettings
        if not corpaysettings:
            raise ValueError("Company does not have corpay settings")
        return corpaysettings.max_horizon

    def cashflow_notional(self, ref_date: Date, currency: Currency, spot_fx_cache: SpotFxCache):
        notional = 0.0

        cashflows = self.get_cashflows()
        for cf in iter_active_cashflows(cfs=cashflows, ref_date=ref_date, max_days_away=self.max_horizon):
            notional += spot_fx_cache.convert_value(cf.amount, cf.currency, currency)
        return notional

    def tenors(self, ref_date: Date) -> Iterable[Date]:
        tenors = []
        cashflows = self.get_cashflows()
        for cf in iter_active_cashflows(cfs=cashflows, ref_date=ref_date, max_days_away=self.max_horizon):
            tenors.append(cf.pay_date)
        return tenors

    def get_cashflows(self):
        if self.cashflow:
            return [self.cashflow]
        if self.draft_cashflow:
            return [self.draft_cashflow.to_cashflow()]
        if self.installment:
            if self.installment.draftcashflow_set and self.installment.draftcashflow_set.count() > 0:
                return [draft.to_cashflow() for draft in self.installment.draftcashflow_set.all()]
            elif self.installment.cashflow_set and self.installment.cashflow_set.count() > 0:
                return self.installment.cashflow_set.all()
        return []

    def to_cashflows(self, ref_date: Date, base_only=False) -> List[CashFlow]:
        """
        Convert a forward into its component cashflows.
        """
        # Amount is the amount in Base, amount of quote is -forward_price * amount.
        cashflows = []
        # Need to set the account here because the next line returns CashFlowHDL
        account = self.account
        for cf in iter_active_cashflows(cfs=self.get_cashflows(), ref_date=ref_date, max_days_away=self.max_horizon):
            base_amount = cf.amount
            quote_amount = -base_amount * self.estimated_fx_forward_price

            cashflows.append(
                CashFlow(amount=base_amount, currency=self.fxpair.base, date=cf.pay_date, account=account))
            if not base_only:
                cashflows.append(
                    CashFlow(amount=quote_amount, currency=self.fxpair.quote, date=cf.pay_date, account=account))
        return cashflows

    def to_hedge_cashflows(self, ref_date: Date) -> List[CashFlow]:
        cashflows = self.to_cashflows(ref_date=ref_date, base_only=True)
        for cf in cashflows:
            cf.amount *= -self.risk_reduction
        return cashflows

    @property
    def fxpair(self) -> FxPair:
        domestic = self.company.currency
        currencies = [cf.currency for cf in self.get_cashflows()]
        # check that all currencies are the same
        if len(set(currencies)) != 1:
            raise Exception("Not all cashflows have the same currency")
        foreign = currencies[0]
        return FxPair.get_pair_from_currency(foreign, domestic)

    def notional(self, ref_date: Optional[Date] = None) -> float:
        ref_date = ref_date or Date.now()
        return sum(self.notionals(ref_date=ref_date))

    def activate_cashflows(self):
        logger.debug(f"Activating forward (ID={self.id})")
        if not self.installment:
            if self.draft_cashflow:
                self.cashflow = self._activate_draft(self.draft_cashflow)
                self.save()
            else:
                logger.debug(" * Forward (ID={self.id}) has a cashflow with id {self.cashflow.id}")
        else:
            logger.debug(f"Forward (ID={self.id}) is an installment")
            if self.installment.draftcashflow_set.count() > 0:
                logger.debug(f" * Forward (ID={self.id}) has draft cashflows")
                for draft_cashflow in self.installment.draftcashflow_set.all():
                    self._activate_draft(draft_cashflow)
            else:
                logger.debug(f" * Forward (ID={self.id}) does not have draft cashflows nothing to activate")

    def _activate_draft(self, draft_cashflow: DraftCashFlow) -> CashFlow:
        logger.debug(f" * Creating cashflow for draft cashflow (ID={draft_cashflow.id})")
        if draft_cashflow.account:
            logger.debug(f" ** Draft cashflow (ID={draft_cashflow.id}) already has an account, ")
            cashflow = draft_cashflow.create_cashflow()
            logger.debug(f" ** Cashflow (ID={cashflow.id}) created for draft cashflow (ID={draft_cashflow.id})")
        else:
            logger.debug(f" ** Draft cashflow (ID={draft_cashflow.id}) does not have an account, ")
            account = Account.create_account(
                name=uuid.uuid4().hex,
                company=self.company,
                account_type=Account.AccountType.LIVE,
                is_active=True,
                is_hidden=True,
            )
            HedgeSettings.create_or_update_settings(
                account=account,
                margin_budget=2e10,
                method="NO_HEDGE",
                custom={
                    "VolTargetReduction": self.risk_reduction,
                    "VaR95ExposureRatio": None,
                    "VaR95ExposureWindow": None,
                },
            )
            logger.debug(f" ** Account (ID={account.id}) created for draft cashflow (ID={draft_cashflow.id})")
            draft_cashflow.account = account
            draft_cashflow.save()
            cashflow = draft_cashflow.create_cashflow()
            draft_cashflow.delete()
            logger.debug(f" ** Cashflow (ID={cashflow.id}) created for draft cashflow (ID={draft_cashflow.id})")
        return cashflow
