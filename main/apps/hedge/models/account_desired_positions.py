from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company, Account, AccountTypes
from main.apps.currency.models.fxpair import FxPair
from main.apps.hedge.models import CompanyHedgeAction

from typing import Optional, Dict, List, Sequence

import logging

logger = logging.getLogger(__name__)


# ==================
# Type definitions
# ==================


class AccountDesiredPositions(models.Model):
    """
    Documents the positions that an account wants to have. Represents the amount that the account told the system to
    get for it, though the actual amount might be rounded, provided via offsets with another account, etc.
    """

    class Meta:
        verbose_name_plural = "Account Desired Positions"
        unique_together = (("company_hedge_action", "account", "fxpair"),)

    # The company hedge action these positions are for.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The company.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False, default=0.)

    # Amount of this fx pair that was desired before liquidity-pool adjustments.
    pre_liquidity_amount = models.FloatField(null=True)

    # ============================
    # Properties
    # ============================

    @property
    def is_long(self) -> bool:
        """ Is this a long position (else short) """
        return 0 <= self.amount

    # ============================
    # Accessors
    # ============================

    def get_liquidity_difference(self):
        if not self.pre_liquidity_amount:
            return 0.
        return self.amount - self.pre_liquidity_amount

    def amount_pre_liquidity(self):
        if not self.pre_liquidity_amount:
            return self.amount
        return self.pre_liquidity_amount

    @staticmethod
    def get_desired_positions_for_account(account: AccountTypes,
                                          time: Optional[Date],
                                          inclusive: bool = True) -> Dict[FxPair, float]:
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)

        hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=account.company, time=time,
                                                                          inclusive=inclusive)
        output = {}
        for obj in AccountDesiredPositions.objects.filter(company_hedge_action=hedge_action, account=account):
            output[obj.fxpair] = obj.amount
        return output

    @staticmethod
    def get_desired_positions_for_all_accounts(company: CompanyTypes,
                                               time: Optional[Date],
                                               inclusive: bool = True
                                               ) -> Dict[Account, Dict[FxPair, float]]:
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)

        hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company, time=time,
                                                                          inclusive=inclusive)
        output = {}
        for obj in AccountDesiredPositions.objects.filter(company_hedge_action=hedge_action):
            output.setdefault(obj.account, {})[obj.fxpair] = obj.amount
        return output

    @staticmethod
    def get_desired_positions_for_company(company: CompanyTypes,
                                          start_time: Optional[Date] = None,
                                          end_time: Optional[Date] = None) -> Sequence['AccountDesiredPositions']:
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        filters = {"company_hedge_action__company": company_}
        if start_time:
            filters["company_hedge_action__time__gte"] = start_time
        if end_time:
            filters["company_hedge_action__time__lte"] = end_time
        return AccountDesiredPositions.objects.filter(**filters)

    @staticmethod
    def get_positions_per_action_per_account(
        company: CompanyTypes,
        start_time: Optional[Date] = None,
        end_time: Optional[Date] = None) -> Dict[CompanyHedgeAction, Dict[Account, List['AccountDesiredPositions']]]:

        positions = AccountDesiredPositions.get_desired_positions_for_company(company=company,
                                                                              start_time=start_time,
                                                                              end_time=end_time)
        output = {}
        for desired in positions:
            output.setdefault(desired.company_hedge_action, {}).setdefault(desired.account, []).append(desired)
        return output

    @staticmethod
    def get_desired_positions_by_fx(live_only: bool,
                                    company: Optional[CompanyTypes] = None,
                                    time: Optional[Date] = None,
                                    hedge_action: Optional[CompanyHedgeAction] = None,
                                    inclusive: bool = True,
                                    pre_liquidity: bool = False) -> Dict[FxPair, Dict[Account, float]]:
        if not hedge_action and not time:
            raise ValueError(f"either a time or a hedge action must be supplied")
        if hedge_action is None and company is None:
            raise ValueError(f"either a hedge action or a company must be supplied")
        if hedge_action is None:
            company_ = Company.get_company(company)
            if not company_:
                raise Company.NotFound(company)
        else:
            company_ = hedge_action.company

        if hedge_action is None:
            hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company_, time=time,
                                                                              inclusive=inclusive)

        filters = {"company_hedge_action": hedge_action,
                   "account__type": Account.AccountType.LIVE if live_only else Account.AccountType.DEMO}

        output = {}
        for obj in AccountDesiredPositions.objects.filter(**filters):
            if pre_liquidity:
                amount = obj.amount if not obj.pre_liquidity_amount else obj.pre_liquidity_amount
            else:
                amount = obj.amount
            output.setdefault(obj.fxpair, {})[obj.account] = amount
        return output

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def add_desired_positions(account: AccountTypes,
                              positions: Dict[FxPair, float],
                              hedge_action: CompanyHedgeAction) -> List['AccountDesiredPositions']:
        if len(positions) == 0:
            return []

        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)

        input = []
        for fxpair, amount in positions.items():
            fx = FxPair.get_pair(fxpair)
            position = AccountDesiredPositions(company_hedge_action=hedge_action,
                                               account=account_,
                                               fxpair=fx,
                                               amount=amount)

            input.append(position)

        if 0 < len(input):
            logger.debug(f"Creating {len(input)} account desired positions for account {account_}:")
            for pos in input:
                logger.debug(f"  * {pos.fxpair}: {pos.amount}")
        else:
            logger.debug(f"No account desired positions.")
        return AccountDesiredPositions.objects.bulk_create(input)

    @staticmethod
    def modify_positions_for_liquidity(liquidity_adjusted_amounts: Dict[FxPair, Dict[Account, float]],
                                       is_live: bool,
                                       hedge_action: CompanyHedgeAction):
        account_type = Account.AccountType.LIVE if is_live else Account.AccountType.DEMO
        desired_positions = AccountDesiredPositions.objects.filter(account__type=account_type,
                                                                   company_hedge_action=hedge_action)
        desired_position_map = {}
        for pos in desired_positions:
            desired_position_map.setdefault(pos.fxpair, {})[pos.account] = pos

        for fxpair, by_account in liquidity_adjusted_amounts.items():
            for account, new_amounts in by_account.items():
                obj = desired_position_map.get(fxpair, {}).get(account, None)
                if obj is not None:
                    obj.pre_liquidity_amount = obj.amount
                    obj.amount = new_amounts
                    obj.save()
                    logger.debug(f"Updated desired position for {account}, {fxpair} "
                                f"from {obj.pre_liquidity_amount} to {obj.amount} "
                                f"(change of {new_amounts - obj.pre_liquidity_amount}).")
                else:
                    logger.warning(f"Could not find a desired position for {account}, {fxpair}")


auditlog.register(AccountDesiredPositions)
