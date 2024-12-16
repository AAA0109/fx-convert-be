from abc import ABCMeta, abstractmethod

from django.db import transaction

from main.apps.currency.models import CurrencyTypes
from main.apps.hedge.models import HedgeSettings, CompanyHedgeAction
from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.services.oms import OMSHedgeService, OMSHedgeServiceInterface, BacktestOMSHedgeService
from main.apps.account.models.company import Company, CompanyTypes
from main.apps.account.models.account import Account, AccountTypes
from main.apps.account.models.cashflow import CashFlow
from main.apps.util import ActionStatus

from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from hdlib.Instrument.CashFlow import CashFlow as CashflowHDL
from hdlib.Instrument.RecurringCashFlowGenerator import RecurringCashFlow as RecurringCashFlowHDL

from typing import Union, Optional, Tuple, Iterable
import pandas as pd

import logging

logger = logging.getLogger(__name__)


class AccountManagerInterface(object, metaclass=ABCMeta):
    @abstractmethod
    def create_account(self, name, company, currencies, raw_cashflows, recurring_cashflows, account_type, is_active):
        """

        :param name: str, name of account
        :param company: CompanyTypes, identifies the company
        :param currencies: Iterable of currencies (optional), the currencies that this account is allowed to have
            hedge positions in. If not supplied, its inferred from the cashflows themselves
        :param raw_cashflows: iterable of raw cashflows (optional)
        :param recurring_cashflows: iterable of recurring cashflows (optional)
        :param account_type: type of account (e.g. DEMO, LIVE, DRAFT)
        :param is_active: Whether the account is active or not.
        :return: action status and the account
        """
        pass

    @abstractmethod
    def get_all_accounts_for_company(self, company):
        pass

    @abstractmethod
    def add_cashflow_to_account(self, account, cashflow):
        pass

    @abstractmethod
    def initialize_company_deactivation(self, company):
        pass

    @abstractmethod
    def finalize_company_deactivation(self, company):
        pass

    @abstractmethod
    def deactivate_account(self, account, unwind_positions):
        pass

    @abstractmethod
    def run_eod(self, company: CompanyTypes) -> ActionStatus:
        """
        Run the EOD account management flow for a company
        :param company: company identifier
        :return: ActionStatus indicating what occurred
        """
        pass

    @abstractmethod
    def initialize_accounts_for_company(self, company, account_type):
        pass


class AccountManagerService(AccountManagerInterface):
    """
    Service responsible for managing an account. Deals with major account events, such as creation, change in
    status, or deactivation
    """

    def __init__(self,
                 oms_hedge_service: OMSHedgeServiceInterface = OMSHedgeService(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService()):
        self._oms_hedge_service = oms_hedge_service
        self._hedge_position_service = hedge_position_service
        self._hedge_request_service = hedge_request_service


    def create_account(self,
                       name: str,
                       company: CompanyTypes,
                       currencies: Optional[Iterable[CurrencyTypes]] = None,
                       raw_cashflows: Iterable[CashflowHDL] = None,
                       recurring_cashflows: Iterable[RecurringCashFlowHDL] = None,
                       account_type: Account.AccountType = Account.AccountType.DRAFT,
                       is_active: bool = True
                       ) -> Account:
        """

        :param name: str, name of account
        :param company: CompanyTypes, identifies the company
        :param currencies: Iterable of currencies (optional), the currencies that this account is allowed to have
            hedge positions in. If not supplied, its inferred from the cashflows themselves
        :param raw_cashflows: iterable of raw cashflows (optional)
        :param recurring_cashflows: iterable of recurring cashflows (optional)
        :param account_type: type of account (e.g. DEMO, LIVE, DRAFT)
        :param is_active: Whether the account is active or not.
        :return: action status and the account
        """

        company_ = Company.get_company(company=company)
        if not company_:
            raise Company.NotFound(company)
        # Setup account
        account = Account.create_account(name=name,
                                         company=company_,
                                         account_type=account_type,
                                         is_active=is_active)

        # Find out the currencies for this account, either supplied, or from cashflows
        if not currencies and (raw_cashflows or recurring_cashflows):
            currencies = set()
            if raw_cashflows:
                for cf in raw_cashflows:
                    currencies.add(cf.currency)
            if recurring_cashflows:
                for cf in recurring_cashflows:
                    currencies.add(cf.currency)

        # Add the cashflows to account
        if recurring_cashflows:
            for cf in recurring_cashflows:
                self.add_cashflow_to_account(account=account, cashflow=cf)

        if raw_cashflows:
            for cf in raw_cashflows:
                self.add_cashflow_to_account(account=account, cashflow=cf)

        return account

    def get_all_accounts_for_company(self, company: CompanyTypes) -> Iterable[Account]:
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        return Account.objects.filter(company=company_)

    def add_cashflow_to_account(self, account: AccountTypes, cashflow: Union[CashflowHDL, RecurringCashFlowHDL]):
        if isinstance(cashflow, RecurringCashFlowHDL):
            CashFlow.create_cashflow(account=account,
                                     date=cashflow.start_date,
                                     amount=cashflow.amount,
                                     currency=cashflow.currency,
                                     status=CashFlow.CashflowStatus.ACTIVE,
                                     periodicity=cashflow.periodicity,
                                     end_date=cashflow.end_date)
        else:  # CashflowHDL
            CashFlow.create_cashflow(account=account,
                                     date=cashflow.pay_date,
                                     amount=cashflow.amount,
                                     currency=cashflow.currency,
                                     status=CashFlow.CashflowStatus.ACTIVE,
                                     name=cashflow.name)

    def initialize_company_deactivation(self, company: CompanyTypes) -> Tuple[ActionStatus, bool]:
        # Return ActionStatus, and indication of deactivation was finalized or not
        company = Company.get_company(company=company)
        if not company:
            return ActionStatus.error("Could not find company")

        if company.status == Company.CompanyStatus.DEACTIVATED:
            return ActionStatus.log_and_no_change("Company is already deactivated")

        # 0) Update company status to pending deactivation
        company.status = Company.CompanyStatus.DEACTIVATION_PENDING
        company.save()

        # 1) Close Open Trades  -> Go to OMS, and cancel orders
        status = self._oms_hedge_service.cancel_all_orders_for_company(company=company)
        if status.is_error():
            return status, False

        # 2) Undwind all hedges
        has_open_positions = self._hedge_position_service.has_open_positions(company=company)  # Anything open

        if has_open_positions:
            status = self._submit_unwind_all_hedges_for_company(company=company)
            if status.is_error():
                return status, False

        # 3) Deactive all accounts
        errors = []
        for account in Account.get_active_accounts(company=company):
            status = Account.deactivate_account(account=account)
            if status.is_error():
                errors.append(str(account.id))
        if errors:
            return ActionStatus.log_and_error(f"Error deactivating accounts: {','.join(errors)}")

        # 4) Try to finalize Deactivating the company if possible (else will have to try again later)
        status = self.finalize_company_deactivation(company=company)
        if status.is_success():
            return status, True

        return ActionStatus.log_and_success("Company deactivation initialized"), False

    def finalize_company_deactivation(self, company: CompanyTypes) -> ActionStatus:
        has_open_live_positions = self._hedge_position_service.has_open_positions(
            company=company,
            account_types=(Account.AccountType.LIVE,))  # Live only

        has_open_orders = self._oms_hedge_service.has_open_orders(company=company)
        if not has_open_live_positions and not has_open_orders:
            company.status = Company.CompanyStatus.DEACTIVATED
            company.save()
            return ActionStatus.log_and_success("Company deactivation complete")

        return ActionStatus.log_and_error("Unable to finalize deactivation")

    def deactivate_account(self, account: AccountTypes, unwind_positions: bool = True) -> ActionStatus:
        # Step 1): Unwind Positions
        logger.debug(f"Deactivating account {account}.")
        if unwind_positions:
            status, action = self._submit_unwind_hedge(account=account)
            if not status.is_success():
                return status

        # Step 2): Deactivate the account
        return Account.deactivate_account(account=account)

    def run_eod(self, company: CompanyTypes) -> ActionStatus:
        """
        Run the EOD account management flow for a company
        :param company: company identifier
        :return: ActionStatus indicating what occurred
        """

        company = Company.get_company(company)
        logger.debug(f"Running EOD account management for company {company}.")
        if company.status == Company.CompanyStatus.DEACTIVATION_PENDING:
            logger.debug(f"Company {company} is pending deactivation.")
            return self.finalize_company_deactivation(company=company)

        logger.debug(f"Updating cashflows.")
        update_cashflows = CashFlow.update_pending_cashflows(company=company)
        if update_cashflows:
            return ActionStatus.log_and_success(f"Updated cashflow status for {len(update_cashflows)}")
        return ActionStatus.log_and_no_change(f"No account mgmt required for company: {company.name}")

    def initialize_accounts_for_company(self,
                                        company: CompanyTypes,
                                        account_type=Account.AccountType.LIVE) -> Iterable[Account]:
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        accounts_to_create = ['low', 'moderate', 'high', 'custom']
        risk_reductions = [0.25, 0.5, 0.85, 0.0]
        logger.debug(f"Initializing account for company {company_}. Creating accounts {accounts_to_create} "
                    f"with risk reductions {risk_reductions}.")

        accounts = []
        with transaction.atomic():
            for i, account_to_create in enumerate(accounts_to_create):
                account = Account()
                account.name = account_to_create
                account.is_active = True
                account.type = account_type
                account.company = company
                account.save()

                HedgeSettings.create_or_update_settings(account=account,
                                                        margin_budget=2e10,
                                                        method="MIN_VAR",
                                                        custom={
                                                            'VolTargetReduction': risk_reductions[i],
                                                            'VaR95ExposureRatio': None,
                                                            'VaR95ExposureWindow': None,
                                                        })
                accounts.append(account)
        return accounts

    def _submit_unwind_hedge(self,
                             company_hedge_action: Optional[CompanyHedgeAction] = None,
                             account: Optional[AccountTypes] = None,
                             settings: Optional[HedgeSettings] = None,
                             ) -> Tuple[ActionStatus, Optional[CompanyHedgeAction]]:
        """
        Unwind a hedge (set all positions to zero), submit the orders to OMS

        :param account: int, the account id (or the account obj)
        :return: Tuple[ActionStatus, Optional[CompanyHedgeAction]], detailing what happened and the company hedge
            action created for the unwind.
        """
        logger.debug(f"Submitting unwind hedge for account {account}.")

        # TODO: need the unwind of a hedge to be done at the same time as hedging the other accounts, so that
        # trades are still submitted / netted together

        # Get the account / hedge settings
        if not settings:
            if not account:
                raise ValueError("You must supply either an account of hedge settings for the account")
            account = Account.get_account(account=account)
            settings = HedgeSettings.get_hedge_settings(account=account)

        if not settings:
            return ActionStatus.log_and_error(f"Account not found: {account}")

        account = settings.account
        settings = settings.to_HedgeAccountSettingsHDL()

        company_hedge_action_ = company_hedge_action
        if not company_hedge_action_:
            logger.debug(f"Creating company hedge action for the unwind hedge.")
            status, company_hedge_action_ = CompanyHedgeAction.add_company_hedge_action(company=account.company)

            if not status.is_success():
                logger.debug(f"Could not create hedge action - cannot continue submitting unwind hedge for "
                            f"account {account}")
                return status, None

        # Get the existing hedge position
        positions = self._hedge_position_service.get_positions_for_account(account=account)
        if positions is None:
            return ActionStatus.log_and_no_change(f"There are no positions to unwind for account: {account}")
        positions = pd.Series(index=positions.keys(), data=positions.values())

        # New Positions, set to zero.
        position_changes = PositionChange(settings=settings,
                                          old_positions=positions,
                                          new_positions=pd.Series(0, index=positions.index))

        status = self._hedge_request_service.create_account_hedge_requests(
            company_hedge_action=company_hedge_action_, position_changes=position_changes)

        logger.debug(f"Done submitting unwind hedge for account {account}.")
        return status, company_hedge_action_

    def _submit_unwind_all_hedges_for_company(self,
                                              company: Company) -> ActionStatus:
        """
        Unwind all hedges for a company
        :param company: Company, which company to unwind for
        :return: ActionStatus
        """
        # TODO: need to unwind them all in a single OMS order sent ... just set all to zero.. need to do so in
        #  a way that doesnt leave any residual in account

        logger.debug(f"Unwinding all hedges for company: {company.get_name()}")
        accounts = Account.get_account_objs(company=company)
        errors = False
        for account in accounts:
            try:
                self._submit_unwind_hedge(account=account)
            except Exception as e:
                logger.error(f"Error unwinding account {account.get_name()} for company {company.get_name()}: {e}")
                errors = True

        return ActionStatus.log_and_success(f"Unwound all hedges for {company.get_name()}") if not errors \
            else ActionStatus.log_and_error(f"Error unwinding some hedges for {company.get_name()}")


class BacktestAccountManagerService(AccountManagerService):
    def __init__(self,
                 oms_hedge_service: OMSHedgeServiceInterface = BacktestOMSHedgeService(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 hedge_request_service: AccountHedgeRequestService = AccountHedgeRequestService()):
        super().__init__(oms_hedge_service=oms_hedge_service,
                         hedge_position_service=hedge_position_service,
                         hedge_request_service=hedge_request_service)

    def run_eod(self, company: CompanyTypes) -> ActionStatus:
        logger.debug(f"Running backtest EOD account management for company {company}.")
        return ActionStatus.log_and_no_change(f"No account mgmt required for company: {company.name}")

