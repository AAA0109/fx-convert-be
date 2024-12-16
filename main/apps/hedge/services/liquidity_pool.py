from typing import Optional, Dict, List

import numpy as np

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.currency.models import FxPair
from main.apps.hedge.models import AccountDesiredPositions, CompanyHedgeAction, LiquidityPoolRecord, \
    CompanyHedgeActionTypes


class LiquidityData:
    """
    LiquidityData encapsulates all the information about the account's desired positions, company's net exposures,
    and company's liquidity pool useage.
    """

    def __init__(self,
                 fxpair: FxPair,
                 pool_record: LiquidityPoolRecord,
                 account_desired_positions: List[AccountDesiredPositions]):
        self._fxpair = fxpair
        self._pool_record = pool_record
        self._account_desired_positions = account_desired_positions

    @property
    def fxpair(self) -> FxPair:
        """
        Get the Fx pair that this LiquidityData is for.
        """
        return self._fxpair

    @property
    def pool_record(self) -> LiquidityPoolRecord:
        """
        Get the LiquidityPoolRecord from the LiquidityData.
        """
        return self._pool_record

    @property
    def account_desired_positions(self) -> List[AccountDesiredPositions]:
        """
        Get the list of accounts' desired positions.
        """
        return self._account_desired_positions

    @property
    def net_exposure(self):
        """ Get the net exposure the company had to the Fx pair. """
        return self._pool_record.total_exposure

    @property
    def liquidity_change(self):
        """
        The net change in (account level) positions that had to be made in each direction to compensate for liquidity
        pool changes.
        """
        diff = 0.
        for pos in self._account_desired_positions:
            diff += np.abs(pos.get_liquidity_difference())
        return 0.5 * diff

    @property
    def pool_size(self):
        """
        The 'liquidity pool size,' i.e. the net exposure minus the net desired position.
        """
        return self.net_exposure - self.net_desired_position

    @property
    def net_desired_position(self):
        """
        The company's net desired position.
        """
        net = 0.
        for pos in self._account_desired_positions:
            net += pos.amount
        return net

    @property
    def fractional_utilization(self):
        """
        What fraction of the liquidity pool is being 'utilized.'
        """
        return np.abs(self.liquidity_change / self.pool_size)


class LiquidityPoolService:
    @staticmethod
    def get_pool_utilization(fxpair: Optional[FxPair] = None,
                             start_date: Optional[Date] = None,
                             end_date: Optional[Date] = None,
                             company: Optional[Company] = None,
                             account: Optional[Account] = None) -> Dict[CompanyHedgeAction, Dict[FxPair, float]]:
        if company is None and account is None:
            raise ValueError(f"one of account and company must be provided")

        filters = {}
        if fxpair:
            filters["fxpair"] = fxpair
        if start_date:
            filters["company_hedge_action__time__gte"] = start_date
        if end_date:
            filters["company_hedge_action__time__lte"] = end_date

        if company:
            filters["account__company"] = company
        elif account:
            filters["account"] = account

        utilization = {}
        for obj in AccountDesiredPositions.objects.filter(**filters):
            if obj.pre_liquidity_amount:
                utilization.setdefault(obj.company_hedge_action, {})[obj.fxpair] \
                    = obj.pre_liquidity_amount - obj.amount
            else:
                utilization.setdefault(obj.company_hedge_action, {})[obj.fxpair] = 0.
        return utilization

    @staticmethod
    def get_data_for_hedge_action(company_hedge_action: CompanyHedgeActionTypes) -> Dict[FxPair, LiquidityData]:
        """
        Get a map from Fx pairs to the liquidity data for that pair.
        """
        action = CompanyHedgeAction.get_action(company_hedge_action)
        if not action:
            raise ValueError(f"could not find company hedge action from {company_hedge_action}")

        pool_records = list(LiquidityPoolRecord.objects.filter(company_hedge_action=company_hedge_action))
        account_desired_positions = list(
            AccountDesiredPositions.objects.filter(company_hedge_action=company_hedge_action))

        pool_record_by_fx, desired_by_fx = {}, {}
        for record in pool_records:
            pool_record_by_fx[record.fxpair] = record
        for pos in account_desired_positions:
            desired_by_fx.setdefault(pos.fxpair, []).append(pos)

        # Note: The two sets of keys should be identical.
        all_fxpair = set(pool_record_by_fx.keys()).union(desired_by_fx.keys())
        all_data = {}
        for fxpair in all_fxpair:
            data = LiquidityData(fxpair=fxpair,
                                 pool_record=pool_record_by_fx.get(fxpair, None),
                                 account_desired_positions=desired_by_fx.get(fxpair, None))
            all_data[fxpair] = data

        return all_data
