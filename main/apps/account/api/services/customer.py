import logging
from typing import Optional, Iterable, Tuple, Union, List

import numpy as np
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Model

from hdlib.DateTime.Date import Date
from hdlib.Instrument.CashFlow import CashFlow as CashflowHDL
from hdlib.Instrument.RecurringCashFlowGenerator import RecurringCashFlow as RecurringCashFlowHDL

import main.libs.pubsub.publisher as pubsub
import main.apps.oems.services.cny_execution_service as cny_execution_service
from django.conf import settings
from main.apps.account.models import Account, Company, AccountTypes, User, CompanyTypes
from main.apps.account.models import CashFlow
from main.apps.account.models.installment_cashflow import InstallmentCashflow
from main.apps.billing.models import Fee
from main.apps.currency.models import CurrencyTypes, Currency, CurrencyMnemonic, FxPair
from main.apps.hedge.models import HedgeSettings
from main.apps.hedge.services.account_manager import AccountManagerService
from main.apps.margin.services.margin_service import DefaultMarginProviderService
from main.apps.margin.services.what_if import DefaultWhatIfMarginInterface
from main.apps.util import get_or_none
from main.apps.core.auth.tokens import account_activation_token_generator

logger = logging.getLogger(__name__)
PrimaryKey = int
what_if_service = DefaultWhatIfMarginInterface()


class CustomerAPIService:
    """
    API object that provides a static interface that is a unified set of function that can be used to create and mutate
    company- and account-related data.
    """

    def __init__(self):
        self._account_manager = AccountManagerService()

    # ====================================================================
    #  User management.
    # ====================================================================

    def create_user(self, first_name: str, last_name: str, email: str, password: str, phone: str,
                    timezone: str) -> User:

        try:
            user, created = User.objects.get_or_create(email=email, is_active=False)
        except IntegrityError as e:
            if 'already exists' in str(e).lower():
                raise User.AlreadyExists(email)
            raise e

        user.first_name = first_name
        user.last_name = last_name
        if password:
            user.set_password(password)
        user.phone = phone
        user.timezone = timezone
        user.save()
        pubsub.publish("customer.user.create", {"user_id": user.id})
        return user

    def update_user(self, user_id: int, first_name: str, last_name: str, email: Optional[str],
                    phone: Optional[str], timezone: Optional[str]) -> User:
        user = User.objects.get(pk=user_id)
        if not user:
            raise User.NotFound(user_id)
        if email:
            user.email = email
        if timezone:
            user.timezone = timezone
        if phone:
            user.phone = phone
        user.last_name = last_name
        user.first_name = first_name
        user.save()
        pubsub.publish("customer.user.update", {"user_id": user.id})

        return user

    def update_user_group(self, user: User, group: str):
        user.groups.clear()
        group = Group.objects.get(name=group)
        user.groups.add(group)
        user.save()
        return user

    # ====================================================================
    #  Company management.
    # ====================================================================

    def create_company(self, company_name: str, currency: Union[CurrencyMnemonic, Currency]) -> \
        Tuple[Company, Iterable[Account]]:

        """
        Create a company.

        :param company_name: str, The name of the company to create.
        :param currency: str, The reporting or domestic currency of a company, as a currency mnemonic, e.g. USD, JPY,
            EUR, etc.
        """
        currency_ = Currency.get_currency(currency)
        if not currency_:
            raise Currency.NotFound(currency)
        with transaction.atomic():
            company = Company.create_company(name=company_name, currency=currency_)
            accounts = self._account_manager.initialize_accounts_for_company(company)
            cny_execution_service.initialize_company(company)
            pubsub.publish("customer.company.create", {"company_id": company.id})

        return company, accounts

    def deactivate_company(self, company_id: PrimaryKey):
        """
        Deactivate a company. Note that this will lead to all accounts for the company being deactivated and all hedges
        being unwound. The company is not immediately deactivated, it's state is changed to DEACTIVATION_PENDING,
        to allow the system to gracefully unwind its positions.
        """
        company = Company.get_company(company_id)
        if not company:
            raise Company.NotFound(company_id)
        company.status = Company.CompanyStatus.DEACTIVATION_PENDING
        company.save()

        pubsub.publish("customer.company.deactivate", {"company_id": company.id})

    # ====================================================================
    #  Account management.
    # ====================================================================

    def create_account_for_company(self,
                                   company_id: PrimaryKey,
                                   account_name: str,
                                   currencies: Optional[Iterable[CurrencyTypes]] = None,
                                   account_type: Account.AccountType = Account.AccountType.DRAFT,
                                   raw_cashflows: Iterable[CashflowHDL] = None,
                                   recurring_cashflows: Iterable[RecurringCashFlowHDL] = None,
                                   is_active: bool = True) -> Account:
        """
        Create an account for a company. Optionally, the account can be created with some raw and / or recurring
        cashflows. If these are not provided, a list of currencies that the account is allowed to trade in must be
        provided. It is permissible to provide both the currencies list *and* cashflows.
        """
        account = self._account_manager.create_account(name=account_name,
                                                       company=company_id,
                                                       currencies=currencies,
                                                       account_type=account_type,
                                                       raw_cashflows=raw_cashflows,
                                                       recurring_cashflows=recurring_cashflows,
                                                       is_active=is_active)
        pubsub.publish("customer.account.create", {"account_id": account.id})

        return account

    def activate_account(self, account: Union[PrimaryKey, Account]) -> Account:
        """ Activate an account. """
        account_ = Account.get_account(account=account)
        if account_ is None:
            raise Account.NotFound(account)

        account_.is_active = True
        account_.save()
        pubsub.publish("customer.account.activate", {"account_id": account_.id})

        return account_

    def deactivate_account(self, account: Union[PrimaryKey, Account]) -> Account:
        """ Deactivate an account. """
        account_ = Account.get_account(account=account)
        if account_ is None:
            raise Account.NotFound(account)

        account_.is_active = False
        account_.save()
        pubsub.publish("customer.account.deactivate", {"account_id": account_.id})

        return account

    def set_hedge_policy_for_account(self,
                                     account_id: PrimaryKey,
                                     method: str,
                                     margin_budget: float,
                                     max_horizon: int = np.inf,
                                     custom_settings: dict = None) -> HedgeSettings:
        """ Set an account's hedge policy. """
        hedge_settings, _ = HedgeSettings.create_or_update_settings(
            account=account_id,
            margin_budget=margin_budget,
            method=method,
            max_horizon_days=max_horizon,
            custom=custom_settings)
        pubsub.publish("customer.account.hedge.update",
                       {"account_id": account_id, "hedge_setting_id": hedge_settings.id})
        return hedge_settings

    @get_or_none
    def get_hedge_policy_for_account(self, account_id: PrimaryKey) -> HedgeSettings:
        # NOTE(Nate): Are we handling errors here? get_hedge_settings can throw, should we catch and return None?
        hedge_settings = HedgeSettings.get_hedge_settings(account=account_id)
        return hedge_settings

    # ====================================================================
    #  Cashflows
    # ====================================================================

    def add_cashflow(self,
                     user: User,
                     account_id: AccountTypes,
                     date: Date,
                     currency_id: CurrencyTypes,
                     amount: float,
                     name: str,
                     description: Optional[str],
                     periodicity: Optional[str],
                     calendar: Optional[CashFlow.CalendarType],
                     end_date: Optional[Date],
                     roll_convention: Optional[CashFlow.RollConvention],
                     installment_id: Union[InstallmentCashflow, int],
                     include_pending_margin_in_margin_check=False) -> CashFlow:
        """Add a cashflow to an account via a cashflow object. This saves the cashflow with the account, and publishes
        the addition of a new cashflow"""
        logger.debug(f"Adding cashflow to account {account_id}")
        cny = Currency.get_currency(currency_id)

        account_ = Account.get_account(account=account_id)
        company = account_.company
        if account_ is None:
            raise Account.NotFound(account_id)
        logger.debug(f"Performing a margin check for account {account_id}")
        # We get active and pending activation cashflows only, as we don't want to include pending deactivation
        # or pending margin.
        cashflows = list(CashFlow.get_company_active_cashflows(
            account_.company,
            include_pending_margin=include_pending_margin_in_margin_check))
        cashflow = CashFlow(account=account_id,
                            date=date,
                            currency=cny,
                            amount=amount,
                            name=name,
                            status=CashFlow.CashflowStatus.ACTIVE,
                            description=description,
                            periodicity=periodicity,
                            calendar=calendar,
                            end_date=end_date,
                            installment_id=installment_id,
                            roll_convention=roll_convention)
        cashflows.append(cashflow)
        if settings.CASHFLOW_API_CONFIG["BYPASS_MARGIN_CHECK"]:
            logger.debug("Bypassing margin check")
            status = CashFlow.CashflowStatus.PENDING_ACTIVATION
        else:
            status = self.get_status_after_margin_check(company=company, cashflows=cashflows, user=user)

        logger.debug(f"Adding cashflow to account {account_id} with status {status}")
        cash = CashFlow.create_cashflow(
            account=account_id,
            date=date,
            currency=currency_id,
            amount=amount,
            name=name,
            status=status,
            description=description,
            periodicity=periodicity,
            calendar=calendar,
            end_date=end_date,
            installment_id=installment_id,
            roll_convention=roll_convention,
            save=True)

        cash.save()
        pubsub.publish("customer.account.cashflow.add",
                       {"account_id": cash.account_id, 'cashflow_id': cash.id})
        return cash

    def remove_cashflow(self, account_id: PrimaryKey, cashflow_id: PrimaryKey):
        """
        Remove a cashflow from an account.
        WARNING: Irreversible.
        """
        cashflow = CashFlow.get_cashflow(cashflow_id=cashflow_id)
        if cashflow:
            # If the cashflow was never activated, delete fees associated with this cashflow
            if cashflow.status == CashFlow.CashflowStatus.PENDING_ACTIVATION:
                # delete fees
                Fee.objects.filter(cashflow=cashflow).delete()
            if cashflow.status == CashFlow.CashflowStatus.PENDING_MARGIN:
                fees = Fee.objects.filter(cashflow=cashflow)
                if Fee.objects.filter(cashflow=cashflow).count() == 1:
                    fees.delete()
            cashflow.status = CashFlow.CashflowStatus.PENDING_DEACTIVATION
            cashflow.save()
            pubsub.publish("customer.account.cashflow.remove",
                           {"account_id": cashflow.account_id, 'cashflow_id': cashflow.id})

    def edit_cashflow(self,
                      account_id: PrimaryKey,
                      cashflow_id: PrimaryKey,
                      pay_date: Date,
                      currency_id: CurrencyTypes,
                      amount: float,
                      name: str,
                      description: Optional[str],
                      periodicity: Optional[str],
                      calendar: Optional[CashFlow.CalendarType],
                      end_date: Optional[Date],
                      roll_convention: Optional[CashFlow.RollConvention],
                      installment_id: Union[InstallmentCashflow, int]) -> CashFlow:
        """
        Replace an existing cashflow with a new one, effectively 'updating' or 'editing' a cashflow (deletes the old
        one, creates a new one).
        The cashflow must have the same name as an existing cashflow, which it is editing. The name must not
        be None.
        """

        try:
            cashflow_db = CashFlow.objects.get(pk=cashflow_id, account=account_id)
        except Model.DoesNotExist:
            raise CashFlow.NotFound(account_id, cashflow_id)
        status = cashflow_db.status
        if cashflow_db.amount != amount or \
            cashflow_db.date != pay_date or \
            cashflow_db.periodicity != periodicity or \
            cashflow_db.calendar != calendar or \
            cashflow_db.roll_convention != roll_convention or \
            cashflow_db.end_date != end_date:
            status = CashFlow.CashflowStatus.PENDING_ACTIVATION

        new_cashflow = CashFlow.edit_cashflow(
            cashflow=cashflow_db, date=pay_date,
            currency=Currency.get_currency(currency_id), amount=amount,
            name=name, status=status, description=description, periodicity=periodicity, calendar=calendar,
            end_date=end_date, installment_id=installment_id, roll_convention=roll_convention)
        pubsub.publish("customer.account.cashflow.edit", {"account_id": account_id, 'cashflow_id': cashflow_id})
        return new_cashflow

    def approve_cashflow(self, cashflow_id: PrimaryKey):
        cashflow = CashFlow.get_cashflow(cashflow_id=cashflow_id)
        cashflow.status = CashFlow.CashflowStatus.PENDING_ACTIVATION
        cashflow.save()
        return cashflow

    def create_installment(self, company: CompanyTypes,
                           name: str,
                           cashflows: Optional[Iterable[CashFlow]] = None) -> InstallmentCashflow:
        installment = InstallmentCashflow.create_installment(company_id=company,
                                                             installment_name=name,
                                                             cashflows=cashflows)
        pubsub.publish("customer.account.installment.add",
                       {"company_id": installment.company_id, 'installment_id': installment.id})
        return installment

    def edit_installment(self, installment_id: Union[InstallmentCashflow, int, str],
                         company_id: CompanyTypes, name: str) -> InstallmentCashflow:
        installment = InstallmentCashflow.get_installment(company_id=company_id, installment_id=installment_id)
        if not installment:
            raise InstallmentCashflow.NotFound(installment_id)
        installment.installment_name = name
        with transaction.atomic():
            installment.save()
            pubsub.publish("customer.account.installment.edit",
                           {"company_id": installment.company_id, 'installment_id': installment.id})
        return installment

    def remove_installment(self, company_id: CompanyTypes, installment_id: Union[InstallmentCashflow, int, str]):
        installment = InstallmentCashflow.get_installment(company_id=company_id, installment_id=installment_id)

        if not installment:
            raise InstallmentCashflow.NotFound(installment_id)
        with transaction.atomic():
            installment.cashflow_set.update(status=CashFlow.CashflowStatus.PENDING_DEACTIVATION)
            pubsub.publish("customer.account.installment.remove",
                           {"company_id": installment.company_id, 'installment_id': installment.id})

    def activate_user(self, user: User, activation_token: str):
        if account_activation_token_generator.check_token(user, activation_token):
            user.is_active = True
            user.save()
            return True
        return False

    def get_status_after_margin_check(self, company: CompanyTypes, cashflows: List[CashFlow],
                                      user: User) -> CashFlow.CashflowStatus:
        """
        Get the status of a cashflow after margin check.
        """
        margin_detail_new = what_if_service.get_margin_details_what_if_after_trades(
            date=Date.today(), company=company, new_cashflows=cashflows)
        margin_health = margin_detail_new.get_margin_health()
        # Margin health check first
        if margin_health.is_unhealthy:
            return CashFlow.CashflowStatus.PENDING_MARGIN
        # Permission check
        user_groups = [group.name for group in user.groups.all()]
        if len(user_groups) == 0:
            raise PermissionError("User does not have a permission group, unable to set cashflow status")
        if User.UserGroups.CUSTOMER_MANAGER in user_groups or User.UserGroups.CUSTOMER_ADMIN in user_groups:
            return CashFlow.CashflowStatus.PENDING_ACTIVATION
        if User.UserGroups.CUSTOMER_CREATOR in user_groups:
            return CashFlow.CashflowStatus.PENDING_APPROVAL
        if User.UserGroups.CUSTOMER_VIEWER in user_groups:
            raise PermissionError("User does not have permission to create cashflow")
