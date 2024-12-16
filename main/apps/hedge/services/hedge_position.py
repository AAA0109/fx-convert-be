import logging
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.Hedge.Cash.CashPositions import VirtualFxPosition, CashPositions
from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.DateTime.Date import Date
from hdlib.Utils.PnLCalculator import PnLCalculator

from main.apps.hedge.models import CompanyEvent
from main.apps.hedge.models import FxPosition
from main.apps.util import ActionStatus
from main.apps.account.models import CompanyTypes, Company
from main.apps.account.models.account import Account, AccountTypes
from main.apps.currency.models.fxpair import FxPair, FxPairTypes, Currency
from main.apps.hedge.models.company_hedge_action import CompanyHedgeAction

from typing import List, Union, Optional, Sequence, Tuple, Dict, Iterable
import numpy as np

logger = logging.getLogger(__name__)


class HedgePositionService(object):
    """
    Service providing details about existing fx hedge positions.
    """

    def get_first_positions_event(self,
                                  account: Optional[AccountTypes] = None,
                                  company: Optional[CompanyTypes] = None) -> Optional[CompanyHedgeAction]:

        """
        Get the company hedge action associated with the creation of the first positions on record for either an
            account or the company as a whole
        :param account: Account identifier, if supplied then we find the company action leading to first positions
            for the account
        :param company: Company identifier, if supplied then we find the company action leading to first positions
            for the company as a whole
        :return: CompanyEvent, if found, else None
        """
        if account is None and company is None:
            raise ValueError(f"either company or account must be provided")

        filters = {}
        if account:
            account_ = Account.get_account(account)
            if not account_:
                raise Account.NotFound(account)
            filters["account"] = account_
        if company:
            company_ = Company.get_company(company=company)
            if not company_:
                raise Company.NotFound(company)
            filters["account__company"] = company_

        # Sort ascending order, take the first one.
        q = FxPosition.objects.filter(**filters).order_by('company_event__time').first()
        if q:
            return q.first().company_event
        return None

    def has_open_positions(self,
                           company: CompanyTypes,
                           time: Optional[Date] = None,
                           account_types: Optional[Iterable[Account.AccountType]] = None) -> bool:
        """
        Check if a company has any existing hedge positions
        :param company: CompanyTypes, which company to look for
        :param time: Date, time at which we are checking if the company had open positions.
        :param account_types: Iterable of AccountTypes (optional), if supplied only consider these types
        :return: bool, True if at least one position found, and it has nonzero holdings
        """
        positions, event = FxPosition.get_position_objs(company=company,
                                                        account_types=account_types,
                                                        time=time)
        if len(positions) == 0:
            return False
        for position in positions:
            if position.amount != 0:
                return True
        return False

    def get_total_value(self,
                        spot_fx_cache: SpotFxCache,
                        account: Optional[Account] = None,
                        company: Optional[Company] = None,
                        date: Optional[Date] = None,
                        ignore_domestic: bool = False
                        ) -> Tuple[float, Currency]:
        """
        Get the total value in domestic currency of existing hedging positions for an account or the entire company
        :param spot_fx_cache: SpotFxCache
        :param account: Account (optional), if supplied get the total value in this account only
        :param company: Company (optional), if supplied get the total value across all accounts for this company
        :param date: Date (optional), if supplied get total value as of this date, else the latest value
        :param ignore_domestic: bool, if true ignore all holdings in domestic currency
        :return: [value, Currency], the account value in the domestic currency
        """
        if not company and not account:
            raise ValueError("You must supply either an account or a company")
        if company and account:
            raise ValueError("You can only supply one of company or account")

        cash_positions, _ = self.get_cash_positions(account=account, company=company, date=date)
        domestic = account.company.currency if company is None else company.currency
        total = 0
        for currency, value in cash_positions.cash_by_currency.items():
            # If only counting 'directional' positions, exclude the value of domestic holdings.
            if currency == domestic and ignore_domestic:
                continue
            total += spot_fx_cache.convert_value(value=value, to_currency=domestic, from_currency=currency)
        return total, domestic

    # ============================
    # Get Position Accessors
    # ============================

    def get_position_objects(self,
                             account: Optional[Account] = None,
                             company: Optional[Company] = None,
                             date: Optional[Date] = None) -> Sequence['FxPosition']:
        if account is not None and company is not None:
            raise ValueError("only one of account and company can be specified")
        if account is None and company is None:
            raise ValueError("either account of company must be specified")

        if account is not None:
            return FxPosition.get_position_objs(account=account, time=date)[0]
        else:
            return FxPosition.get_position_objs(company=company, time=date)[0]

    def get_virtual_fx_positions(self,
                                 account: Optional[Account] = None,
                                 company: Optional[Company] = None,
                                 date: Optional[Date] = None):
        position_objs = self.get_position_objects(account=account, company=company, date=date)
        virtual_fx = []
        for position in position_objs:
            virtual_fx.append(VirtualFxPosition(fxpair=position.fxpair,
                                                amount=position.amount,
                                                ave_price=position.average_price[0]))
        return virtual_fx

    def get_cash_positions(self,
                           account: Optional[Account] = None,
                           company: Optional[Company] = None,
                           date: Optional[Date] = None) -> Tuple[CashPositions, Sequence[FxPosition]]:
        position_objs = self.get_position_objects(account=account, company=company, date=date)
        cash_positions = CashPositions()
        for position in position_objs:
            cash_positions.add_cash_from_single_fx_spot(fxpair=position.fxpair.to_FxPairHDL(),
                                                        amount=position.amount,
                                                        ave_price=position.average_price[0])
        return cash_positions, position_objs

    def get_all_positions_for_accounts_for_company_by_pair(
        self,
        company: CompanyTypes,
        account_types: Optional[Iterable[Account.AccountType]] = None,
        time: Optional[Date] = None) -> Dict[FxPairHDL, Dict[Account, float]]:
        """
        Get a dictionary from FX pair name to a dictionary from account to the position of the FX pair in that account.

        :param company: CompanyTypes, The company whose positions we want to get.
        :param account_types: Iterable, An alternative method of specifying what types of accounts we want.
        :param time: Date, Date as of which we want the positions.
        """

        last_positions, event = FxPosition.get_position_objs(company=company, time=time, account_types=account_types)

        positions_by_fx = {}
        for position in last_positions:
            positions_by_fx[position.fxpair.to_FxPairHDL()] = positions_by_fx.get(position.fxpair.to_FxPairHDL(), {})
            positions_by_fx[position.fxpair.to_FxPairHDL()][position.account] = position.amount

        return positions_by_fx

    def get_positions_for_company_by_account(self,
                                             company: CompanyTypes,
                                             account_types: Optional[Iterable[Account.AccountType]] = None,
                                             time: Date = None
                                             ) -> Dict[Account, List['FxPosition']]:
        """ Get a company's most recent positions. """
        # Get most recent positions.
        company_ = Company.get_company(company)
        if not company_:
            raise ValueError(f"could not find company from {company}")

        filters = {"company_event__company": company_}

        if account_types is not None:
            filters["account__type__in"] = account_types
        if time is not None:
            filters["company_event__time__lte"] = time

        positions_by_account = {}
        q = FxPosition.objects.filter(**filters).order_by("-company_event__time")
        if not q:
            return {}
        company_event = q.first().company_event
        acc_positions = q.filter(company_event=company_event)

        for position in acc_positions:
            positions_by_account[position.account] = positions_by_account.get(position.account, []) + [position]
        return positions_by_account

    def get_aggregate_positions_for_company(self,
                                            company: Optional[Company] = None,
                                            account_types: Optional[Iterable[Account.AccountType]] = None,
                                            time: Optional[Date] = None) -> Dict[FxPairHDL, float]:
        """
        Get the Fx positions for a company, aggregated across all accounts.

        :param company: CompanyTypes, identifier for a company
        :param account_types: Iterable, An alternative method of specifying what types of accounts we want.
        :return: Dict, the positions in the database, in market traded convention
        """

        # Get most positions, either most recent, or specific to a company hedge action.
        acc_positions, event = FxPosition.get_position_objs(company=company,
                                                            account_types=account_types,
                                                            time=time)

        positions_out: Dict[FxPairHDL, float] = {}
        for position in acc_positions:
            fx_pair = position.fxpair.to_FxPairHDL()
            positions_out[fx_pair] = positions_out.get(fx_pair, 0) + position.amount

        return positions_out

    # ============================
    # Modifiers
    # ============================

    def delete_positions(self,
                         company_hedge_action: CompanyHedgeAction):
        """ Delete the positions associated with a company hedge action. """
        FxPosition.objects.filter(company_hedge_action=company_hedge_action).delete()

    def set_single_position_for_account(self,
                                        account: AccountTypes,
                                        # NOTE: Prefer providing a company event to a company hedge action.
                                        company_hedge_action: CompanyHedgeAction,
                                        fx_pair: FxPairTypes,
                                        amount: float,
                                        spot_rate: float,
                                        company_event: CompanyEvent = None,
                                        old_position: Optional['FxPosition'] = None
                                        ) -> Tuple[ActionStatus, Optional['FxPosition'], float]:
        fx_pair_ = FxPair.get_pair(fx_pair)
        if fx_pair_ is None:
            return ActionStatus.error(f"fx pair {fx_pair} does not exist")

        account_ = Account.get_account(account)
        if account_ is None:
            return ActionStatus.error(f"account {account} does not exist")

        if old_position:
            if old_position.account != account_ or old_position.fxpair != fx_pair_:
                return ActionStatus.error("The old position you supplied is inconsistent with the new one"), None, 0
        else:
            old_position = FxPosition.get_single_position_obj_for_account(account=account_, fx_pair=fx_pair_)

        realized_pnl = 0  # realized PnL in the quote currency
        if amount is None:
            amount = 0

        if old_position and old_position.amount is not None and old_position.amount != 0:
            # Figure out the update to the total price and realized PnL
            old_amount = old_position.amount
            # Note that average price should be positive, regardless of whether the amount is positive or negative.
            old_avg_price = old_position.total_price / np.abs(old_amount)

            new_total_price = PnLCalculator.calc_total_price(old_amount=old_amount, new_amount=amount,
                                                             old_price_avg=old_avg_price, new_price_avg=spot_rate)
            realized_pnl = PnLCalculator.calc_realized_pnl(old_amount=old_amount, new_amount=amount,
                                                           old_price_avg=old_avg_price, new_price_avg=spot_rate)
        else:
            new_total_price = spot_rate * abs(amount)

        try:
            if company_event is None:
                company_event = CompanyEvent.get_or_create_event(company=account.company,
                                                                 time=company_hedge_action.time)
                # There are account Fx positions associated with this event.
                company_event.has_account_fx_snapshot = True
                company_event.save()

            obj, created = FxPosition.objects.update_or_create(account=account,
                                                               company_event=company_event,
                                                               fxpair=fx_pair_,
                                                               amount=amount,
                                                               total_price=new_total_price)
            if created:
                return ActionStatus.success("Position Created"), obj, realized_pnl
            else:
                return ActionStatus.success("Position Updated"), obj, realized_pnl
        except Exception as ex:
            logger.error(ex)
            return ActionStatus.error(f"Could not set account position due to error: {ex}"), None, 0
