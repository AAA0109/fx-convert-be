from auditlog.registry import auditlog
from django.db import models
from typing import Union, Optional, List, Tuple, Iterable, Sequence
import numpy as np

from hdlib.DateTime.Date import Date
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPairId
from main.apps.account.models.account import Account, AccountTypes
from main.apps.util import get_or_none, ActionStatus
from main.apps.account.models.company import CompanyTypes, Company

from hdlib.Hedge.Fx.HedgeAccount import HedgeAccountSettings as HedgeAccountSettingsHDL, HedgeMethod

import logging

logger = logging.getLogger(__name__)


class HedgeAccountSettings_DB(HedgeAccountSettingsHDL):
    def __init__(self,
                 account: Account,
                 method: HedgeMethod,
                 margin_budget: float,
                 max_horizon: int = np.inf,
                 custom_settings: dict = None):
        """"""
        super(HedgeAccountSettings_DB, self).__init__(account=account, method=method,
                                                      margin_budget=margin_budget,
                                                      max_horizon=max_horizon,
                                                      custom_settings=custom_settings)

    @property
    def account(self) -> Account:
        # By construction, this will always be a genuine Account (from the DB).
        account = self.get_account()
        if isinstance(account, Account):
            return account
        else:
            raise ValueError(f"it is not possible for HedgeAccountSettings_DB's account to not be a DB Account object")


# TODO(Nate): Can/should this inherit from HedgeAccountSettings/_DB?
class HedgeSettings(models.Model):
    """
    Hedge settings for a particular account. Determines which hedge method to use, etc
    """

    # Account that these settings are tied to (only one hedge settings allowed per account)
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='hedge_settings', null=False,
                                   unique=True)

    # Max time horizon (days) where will consider future cashflows in the hedge
    max_horizon_days = models.IntegerField(null=False, default=365 * 20)

    # Total Budget (in units of domestic currency) for the positions that can be held based on their margin reqs.
    # Note: aggregate margin budgets will also apply, this is to limit the capital devoted to any particular account
    margin_budget = models.FloatField(null=False)

    # Hedging method, maps to an enum
    method = models.CharField(max_length=255, null=False, default="NO_HEDGE")

    custom = models.JSONField(null=True, default=None)

    # Last time the settings were updated
    updated = models.DateTimeField(auto_now_add=True, blank=True)

    def to_HedgeAccountSettingsHDL(self) -> HedgeAccountSettings_DB:
        """
        Convert the model instance to an hdlib settings object.
        :return: HedgeAccountSettingsHDL (the hedge settings)
        """
        try:
            method = HedgeMethod(self.method)
        except Exception:
            raise ValueError(f"The configured hedge method: {self.method}, does not exist")

        return HedgeAccountSettings_DB(account=self.account,
                                       method=method,
                                       margin_budget=self.margin_budget,
                                       max_horizon=self.max_horizon_days,
                                       custom_settings=self.custom)

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_all_accounts_to_hedge(account_types: Sequence[Account.AccountType]
                                  = (Account.AccountType.DEMO, Account.AccountType.LIVE),
                                  company: Optional[CompanyTypes] = None,
                                  include_no_hedge: bool = False
                                  ) -> Iterable['HedgeSettings']:
        """
        Get the hedge settings for all accounts that need to be hedged (all active accounts)
        :param account_types: Tuple of types of account to include when retrieving settings
        :param company: any one of the CompanyTypes (optional), if supplied only get settings for accounts within
            this company
        :return: Iterable through the HedgeSettings objects
        """

        # TODO: Make this time dependent, so we can get historical account settings.

        filters = {
            "account__type__in": account_types,
            "account__is_active": True,
        }
        if company:
            company_ = Company.get_company(company=company)
            if not company_:
                raise ValueError(f"could not find company {company}")
            filters["account__company"] = company_
        qs = HedgeSettings.objects.filter(**filters)
        if not include_no_hedge:
            qs = qs.exclude(method="NO_HEDGE")
        objs: Sequence[HedgeSettings] = qs

        for hedge_settings in objs:
            yield hedge_settings

    @staticmethod
    @get_or_none
    def get_hedge_settings(account: AccountTypes) -> Optional['HedgeSettings']:
        """
        Get HedgeSettings for an account
        :param account: int, the account id (or the account object itself)
        :return: HedgeSettings for account, if exists, else None
        """

        # TODO: Make this time dependent, so we can get historical account settings.

        account_ = Account.get_account(account)
        if not account_:
            raise ValueError(f"could not find account {account}")
        return HedgeSettings.objects.get(account=account_)

    @staticmethod
    def get_hedge_account_settings_hdl(account: AccountTypes) -> Optional[HedgeAccountSettings_DB]:
        """
        Get the Hedge Account Settings for an account. Returns an hdlib compatable settings object, which can
        be supplied to the hedge engines.

        :param account: int, the account id (or the account itself)
        :return: HedgeAccountSettingsHDL (the hedge settings) if found, else None
        """
        settings = HedgeSettings.get_hedge_settings(account=account)
        return settings.to_HedgeAccountSettingsHDL() if settings else None

    # ============================
    # Modifiers
    # ============================

    @staticmethod
    def create_or_update_settings(account: AccountTypes,
                                  margin_budget: float,
                                  method: str = "MIN_VAR",
                                  max_horizon_days: int = 365 * 20,
                                  custom: dict = None) -> Tuple['HedgeSettings', bool]:
        """
        Create hedge settings for an account (update existing ones if settings already exist for that account). Note
        that each account can have only one set of settings.
        :param account: Account or int, identifies which account
        :param margin_budget: float, the maximum daily margin exposure allowed (in units of account's domestic currency)
        :param method: str, the hedge method to use for this account
        :param max_horizon_days: int, the maximum number of days into the future to hedge for this account (ie,
            cashflows beyond this are not taking into account, until they enter this horizon)
        :param custom: dict, dictionary of custom settings.
        :return: tuple (HedgeSettings, bool). The boolean indicates whether the account was created(true) vs
                updated(false)
        """

        # TODO: Allow for settings versions, so we know what the settings were in the past.

        account_ = Account.get_account(account=account)
        if account_ is None:
            raise Account.NotFound(account)

        settings, created = HedgeSettings.objects.update_or_create(
            account=account_,
            defaults={'margin_budget': margin_budget,
                      'method': method,
                      'max_horizon_days': max_horizon_days,
                      'updated': Date.utcnow()})
        if custom:
            settings.custom = custom
            settings.save()
        return settings, created

auditlog.register(HedgeSettings)
