from auditlog.registry import auditlog
from django.db import models
from hdlib.Core.AccountInterface import AccountInterface

from main.apps.account.models.company import Company, CompanyName, CompanyTypes
from main.apps.util import get_or_none, ActionStatus

from typing import Union, List, Iterator, Sequence, Optional, Tuple

import logging

logger = logging.getLogger(__name__)

# =====================================
# Type Definitions
# =====================================
AccountId = int
AccountName = str


class Account(models.Model, AccountInterface):
    """
    Represents a particular Pangea account to which we tie cashflows and establish a hedging strategy.
    Note that a pangea account is an abstraction that allows us to treat collections of cashflows together as a
    separately hedgeable group, that is hedged in isolation of other company cashflows.
    """

    class Meta:
        verbose_name_plural = "accounts"
        unique_together = (("name", "company"),)  # Accounts per company must be uniquely named

    # Company to which account is tied
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='acct_company', null=False)

    # Name of the account
    name = models.CharField(max_length=255)

    # Account creation date
    created = models.DateTimeField(auto_now_add=True, blank=True)

    # Active indicates the account is still in use (else it has been deactivated)
    is_active = models.BooleanField(null=False, default=True)

    # Hidden accounts are used in certain calculations and represent accounts
    # which are meant to be used by the system.
    is_hidden = models.BooleanField(null=False, default=False)

    class AccountType(models.IntegerChoices):
        DRAFT = 0  # A draft account, not yet fully completed, or not configured to run in demo or live mode
        DEMO = 1  # A demo account, used for testing
        LIVE = 2  # Live account, with active hedges

    # Type of the account
    type = models.IntegerField(null=False, default=AccountType.DEMO, choices=AccountType.choices)

    class AccountStrategy(models.IntegerChoices):
        # An account that can execute spot hedges.
        SPOT_HEDGING = 0
        # An account that is executing the parachute hedge strategy. These accounts will have associated ParachuteData.
        PARACHUTE = 1
        # Hard limits - these accounts are spot hedging accounts that also have a parachute component, and will therefore
        # have associated ParachuteData.
        HARD_LIMITS = 2

    # The strategy that is being used for this account.
    strategy = models.IntegerField(null=False, default=AccountStrategy.SPOT_HEDGING, choices=AccountStrategy.choices)

    # =============================================================
    #  AccountInterface methods.
    # =============================================================

    def get_name(self) -> str:
        """ Get the name of the account. """
        return self.name

    def get_company(self) -> Company:
        """ Get the company that owns the account. """
        return self.company

    def get_is_live_account(self) -> bool:
        """ Check if this is a live account """
        return self.type == Account.AccountType.LIVE

    def __hash__(self):
        """ Need to override __hash__ since both model and AccountInterface implement this. """
        return hash(self.get_name() + ":" + self.get_company().get_name())

    def __str__(self):
        """ Need to override __str__ since both model and AccountInterface implement this. """
        return f"{self.get_company()} @ {self.get_name()}"

    def __repr__(self):
        """ Need to override __repr__ since both model and AccountInterface implement this. """
        return f"{self.get_company()} @ {self.get_name()}"

    # =============================================================
    #  Other methods.
    # =============================================================

    def has_hedge_settings(self) -> bool:
        """ Check if this account has hedge settings """
        return hasattr(self, 'hedge_settings')

    def __lt__(self, other: 'Account'):
        return (self.company.name, self.name) < (other.company.name, other.name)

    # ============================
    #  Model Accessors.
    # ============================

    @staticmethod
    @get_or_none
    def get_account(account: Union[AccountId, 'Account'] = None,
                    name: Tuple[CompanyName, AccountName] = None) -> Optional['Account']:
        """
        Get an account if it exists, else return None
        :param account: int, the account_id
        :param name: Tuple[str, str] - tuple of company name and account name
        :return: Account, if found, else None
        """
        if account:
            if isinstance(account, Account):
                return account
            return Account.objects.get(pk=account)
        if name:
            return Account.objects.get(company__name=name[0], name=name[1])
        raise ValueError("You must supply either an account, account id, or a pair of [company_name, account_name]")

    @staticmethod
    def has_live_accounts(company: CompanyTypes, active_only: bool = True) -> bool:
        """
        Returns whether the company has any live accounts
        :param company: the Company identifier
        :param active_only: bool, if true only return true if it has an active live account(s)
        :return: bool, True if company has a live account(s), else false.
        """
        return Account.has_account_of_type(company=company, account_type=Account.AccountType.LIVE,
                                           active_only=active_only)

    @staticmethod
    def get_active_accounts(live_only: bool = False,
                            demo_only: bool = False,
                            company: Optional[CompanyTypes] = None,
                            exclude_hidden=False) -> Sequence['Account']:
        """
        Get all active accounts
        :param live_only: bool, if true only get LIVE accounts. Either this or demo_only can be True, not both.
        :param demo_only: bool, if true only get DEMO accounts. Either this or live_only can be True, not both.
        :param company: CompanyTypes, Company or its id (optional), if supplied get accounts for this company only
        :param exclude_hidden: bool, whether hidden accounts should be excluded
        :return: All active Account objects
        """
        if live_only and demo_only:
            raise ValueError(f"you cannot request live_only=True and demo_only=True")

        if not live_only and not demo_only:
            types = ()
        elif live_only:
            types = (Account.AccountType.LIVE,)
        else:
            types = (Account.AccountType.DEMO,)

        return Account.get_account_objs(company=company,
                                        account_types=types,
                                        active_only=True,
                                        exclude_hidden=exclude_hidden)

    @staticmethod
    def get_account_objs(company: Optional[CompanyTypes] = None,
                         account_types: Tuple[AccountType] = (),
                         strategy_types: Tuple[AccountStrategy] = (),
                         active_only: bool = True,
                         exclude_hidden=False) -> Sequence['Account']:
        """
        Getter method applying various filters
        :param company: Company or its id (optional), if supplied get accounts for this company only
        :param account_types: Tuple[AccountType], which types of accounts to include. If not supplied, then all
            account types are included.
        :param strategy_types: Tuple[AccountStrategy], which account strategies to include. If not supplied, all
            account strategies are included.
        :param active_only: bool, if true only return active accounts
        :return: Account objects satisfying filters (all accounts if no filters)
        """
        filters = {}
        if active_only:
            filters["is_active"] = True
        if account_types and 0 < len(account_types):
            filters["type__in"] = account_types
        if strategy_types and 0 < len(strategy_types):
            filters["strategy__in"] = strategy_types
        if company:
            filters["company"] = Company.get_company(company=company)
        if exclude_hidden:
            filters['is_hidden'] = False
        return Account.objects.filter(**filters)

    @staticmethod
    def has_account_of_type(company: CompanyTypes,
                            account_type: 'Account.AccountType',
                            active_only: bool = True,
                            exclude_hidden: bool = False) -> bool:
        """
        Returns whether the company has any accounts of the specified type.
        :param company: the Company identifier
        :param account_type: AccountType, the type of account to look for
        :param active_only: bool, if true only return true if it has an active account(s) of this type
        :param exclude_hidden: bool, if true don't return hidden accounts
        :return: bool, True if the company has an account of this type
        """
        company_ = Company.get_company(company)
        if not company_:
            return False
        accounts_of_type = Account.get_account_objs(company=company_, account_types=(account_type,),
                                                    active_only=active_only,
                                                    exclude_hidden=exclude_hidden)
        if accounts_of_type:
            return True
        return False

    # ============================
    # Modifiers
    # ============================

    @staticmethod
    def create_account(name: str,
                       company: CompanyTypes,
                       account_type: AccountType = AccountType.DEMO,
                       is_active: bool = True,
                       is_hidden: bool = False) -> 'Account':
        """
        Create a new account
        :param name: str, the name of the account
        :param company: int (company_id), str (name of company), or Company (object) - company identifier
        :param account_type: AccountType enum, e.g. DEMO or LIVE account
        :param is_active: Whether the account is active or not.
        :param is_hidden: Whether this is a hidden account or not.
        :return: Account, if created. If the account already exists, it will raise an exception. If it is unable,
            to create an account (e.g. can't find the company), will also raise exception
        """
        company_ = Company.get_company(company=company)
        if not company_:
            raise Company.NotFound(company)

        return Account.objects.create(
            name=name,
            company=company_,
            type=account_type,
            is_active=is_active,
            is_hidden=is_hidden)

    @staticmethod
    def get_or_create_account(name: str,
                              company: CompanyTypes,
                              account_type: AccountType = AccountType.DEMO,
                              is_active: bool = True) -> 'Account':
        """
        Create a new account if it does not exist, otherwise get the account.
        :param name: str, the name of the account
        :param company: int (company_id), str (name of company), or Company (object) - company identifier
        :param account_type: AccountType enum, e.g. DEMO or LIVE account
        :param is_active: Whether the account is active or not.
        :return: Tuple - first element is the status detailing what happened, second is the account, either created
                or found if it already exists. If error occured during creation, returns None
        """
        company_ = Company.get_company(company=company)
        if not company_:
            raise Company.NotFound(company)

        obj, _ = Account.objects.get_or_create(
            name=name,
            company=company_,
            type=account_type,
            is_active=is_active)
        return obj

    @staticmethod
    def deactivate_account(account: Union[AccountId, 'Account']) -> ActionStatus:
        """
        Deactivate an account. NOTE: this is not safe to perform in isolation. Make sure that this is only
        called by a procedure that first unwinds the existing hedge positions as directed.
        :param account: int, the account id
        :return: AccountChange, Indication of the result of this change
        """
        account = account if isinstance(account, Account) else Account.get_account(account=account)
        if account is None:
            return ActionStatus.error(f"Account {account} doesnt exist")

        if not account.is_active:
            return ActionStatus.no_change("Account is Already Deactivated")

        account.is_active = False
        account.save()
        return ActionStatus.success(message="Account Deactivated")

    @staticmethod
    def remove_account(account_name: str, company: CompanyTypes) -> ActionStatus:
        """
        Delete an account entirely. NOTE: use this method very carefully! You should never call this method unless
        a full deactivation of the account has been triggered. Really, this should only be used for testing purposes,
        as accounts should typically not be deleted in order to maintain a proper audit trail.
        :param account_name: str, name of the account to delete
        :param company: identifier of the company
        :return: ActionStatus, indication of what happened
        """
        company_ = Company.get_company(company)
        if not company_:
            return ActionStatus.log_and_error(f"Cannot remove account since company {company} could not be found.")
        account = Account.objects.filter(name=account_name, company=company_).first()
        if account:
            account.delete()
            return ActionStatus.log_and_success(f"Deleted account {account_name} for company {company}.")
        return ActionStatus.log_and_no_change(f"Could not find account {account_name} for company {company}.")

    # =======================
    # Exceptions
    # =======================

    class NotFound(Exception):
        def __init__(self, account: Union[AccountId, 'Account']):
            if isinstance(account, AccountId):
                super(Exception, self).__init__(f"Account with id:{account} is not found")
            elif isinstance(account, Account):
                super(Exception, self).__init__(f"Account with name:{account} is not found")
            else:
                super(Exception, self).__init__()

    class AlreadyExists(Exception):
        def __init__(self, company: Company, name: str):
            super(Account.AlreadyExists, self).__init__(f"Account:{name} already exists for company: {company}")


# The types that can be used to denote an account.
AccountTypes = Union[AccountId, Account]

auditlog.register(Account)
