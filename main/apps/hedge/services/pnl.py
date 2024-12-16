import logging
from typing import Optional, Sequence, Tuple, Iterable, Dict

import numpy as np
from hdlib.Universe.Universe import Universe

from main.apps.currency.models import FxPair, FxPairName, Currency
from main.apps.hedge.models import FxPosition, AccountHedgeRequest
from main.apps.account.models.account import Account, AccountTypes
from main.apps.account.models.company import CompanyTypes, Company
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from hdlib.Instrument.FxForward import FxForwardInstrument
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.Hedge.Fx.Util.FxPnLCalculator import FxPnLCalculator
from hdlib.DateTime.Date import Date
from main.apps.marketdata.services.universe_provider import UniverseProviderService

logger = logging.getLogger(__name__)


def _get_positions(account: Optional[AccountTypes] = None,
                   company: Optional[CompanyTypes] = None,
                   account_types: Optional[Iterable[Account.AccountType]] = None,
                   date: Optional[Date] = None) -> Tuple[Sequence[FxPosition], Currency]:
    if account:
        positions, event = FxPosition.get_position_objs(account=account, time=date)
        domestic = account.domestic_currency
    elif company:
        company = Company.get_company(company)
        domestic = company.currency
        positions, event = FxPosition.get_position_objs(company=company, account_types=account_types, time=date)
    else:
        raise ValueError("you must supply either an account or company")
    return positions, domestic


def _get_fxforward_positions(account: Optional[AccountTypes] = None,
                             company: Optional[CompanyTypes] = None,
                             account_types: Optional[Iterable[Account.AccountType]] = None,
                             date: Optional[Date] = None) -> Iterable[FxForwardInstrument]:
    if account:
        return FxForwardPosition.get_forwards_for_account(current_time=date, account=account)
    elif company:
        return FxForwardPosition.get_forwards_for_company(current_time=date, company=company,
                                                          account_types=account_types)
    else:
        raise ValueError("you must supply either an account or company")


class PnLData:
    def __init__(self, domestic: Currency, fxspot_pnl: float = 0.0, fxforward_pnl: float = 0.0):
        self.fxspot_pnl = fxspot_pnl
        self.fxforward_pnl = fxforward_pnl
        self.domestic = domestic

    @property
    def total_pnl(self):
        return self.fxspot_pnl + self.fxforward_pnl


class PnLProviderService(object):
    """
    Service responsible for managing pnl of account
    """

    def __init__(self,
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 universe_provider: UniverseProviderService = UniverseProviderService()):
        self._fx_spot_provider = fx_spot_provider
        self._pnl_calculator = FxPnLCalculator()
        self._universe_provider = universe_provider

    def get_hedge_position_value(self,
                                 account: Optional[AccountTypes] = None,
                                 company: Optional[CompanyTypes] = None,
                                 account_types: Optional[Iterable[Account.AccountType]] = None,
                                 date: Optional[Date] = None,
                                 fx_cache: Optional[SpotFxCache] = None) -> Tuple[float, Currency]:
        """
        Get value of positions in domestic currency.
        If no date is supplied, uses to latest date in the system.
        """
        positions, domestic = _get_positions(account=account, company=company, account_types=account_types,
                                             date=date)

        # If you didn't supply an fx cache, we will use the EOD spot cut
        if not fx_cache:
            fx_cache = self._fx_spot_provider.get_eod_spot_fx_cache(date=date)

        value = self._pnl_calculator.get_position_value(fx_cache=fx_cache, positions=positions, currency=domestic)
        return value, domestic

    def get_hedge_position_value_by_holding(self,
                                            fx_cache: SpotFxCache,
                                            account: Optional[AccountTypes] = None,
                                            company: Optional[CompanyTypes] = None,
                                            account_types: Optional[Iterable[Account.AccountType]] = None,
                                            ) -> Tuple[Dict[FxPairName, float], Currency]:
        positions, domestic = _get_positions(account=account, company=company, account_types=account_types,
                                             date=fx_cache.time)
        return self._pnl_calculator.get_position_value_by_holding(fx_cache=fx_cache,
                                                                  positions=positions,
                                                                  currency=domestic), domestic

    def get_realized_pnl(self,
                         spot_fx_cache: SpotFxCache,
                         account: Optional[AccountTypes] = None,
                         company: Optional[CompanyTypes] = None,
                         account_types: Sequence[Account.AccountType] = (),
                         start_date: Optional[Date] = None,
                         end_date: Optional[Date] = None,
                         include_start_date: bool = True) -> PnLData:
        fxspot_pnl = self.get_realized_pnl_fxspot(account=account,
                                                  company=company,
                                                  account_types=account_types,
                                                  start_date=start_date,
                                                  end_date=end_date,
                                                  include_start_date=include_start_date)

        fxforward_pnl = self.get_realized_pnl_fxforward(account=account,
                                                        company=company,
                                                        account_types=account_types,
                                                        start_date=start_date,
                                                        end_date=end_date,
                                                        include_start_time=include_start_date,
                                                        spot_fx_cache=spot_fx_cache)

        domestic = company.currency if company else account.company.currency
        return PnLData(domestic=domestic, fxspot_pnl=fxspot_pnl, fxforward_pnl=fxforward_pnl)

    def get_realized_pnl_fxspot(self,
                                account: Optional[AccountTypes] = None,
                                company: Optional[CompanyTypes] = None,
                                account_types: Sequence[Account.AccountType] = (),
                                start_date: Optional[Date] = None,
                                end_date: Optional[Date] = None,
                                include_start_date: bool = True) -> float:
        """
        Get realized PnL for Fx spot positions over all closed trades for an account (or company), in domestic/account
        currency.
        """
        if account:
            account = Account.get_account(account)
        elif company:
            company = Company.get_company(company)
        else:
            raise ValueError("You must supply either an account or a company")

        requests = AccountHedgeRequest.get_hedge_request_objs(account=account,
                                                              company=company,
                                                              account_types=account_types,
                                                              start_date=start_date,
                                                              end_date=end_date,
                                                              include_start_date=include_start_date)
        pnl_domestic = 0
        for request in requests:
            if not request.is_closed or request.requested_amount == 0:
                continue
            if np.isnan(request.realized_pnl_domestic):
                logger.error(f"In PnLProviderService.get_realized_pnl: AccountHedgeRequests id={request.id}, for "
                             f"account {account} made on date {request.company_hedge_action.time} has NaN realized "
                             f"PnL, not adding to the record of PnL domestic.")
                continue
            pnl_domestic += request.realized_pnl_domestic

        return pnl_domestic

    def get_realized_pnl_fxforward(self,
                                   spot_fx_cache: SpotFxCache,
                                   account: Optional[AccountTypes] = None,
                                   company: Optional[CompanyTypes] = None,
                                   account_types: Sequence[Account.AccountType] = (),
                                   start_date: Optional[Date] = None,
                                   end_date: Optional[Date] = None,
                                   include_start_time: bool = True) -> float:
        """
        Get the PnL (in domestic currency) due to all forwards that were unwound (or settled) during a specified
        period of time.
        """
        forwards = FxForwardPosition.get_unwound_forwards(account=account, company=company,
                                                          account_types=account_types,
                                                          start_time=start_date, end_time=end_date,
                                                          include_start_time=include_start_time)
        pnl = 0.0
        domestic = company.currency if company else account.company.currency
        for fwd in forwards:
            fwd_pnl = fwd.pnl
            pnl += spot_fx_cache.convert_value(value=fwd_pnl, from_currency=fwd.fxpair.base, to_currency=domestic)
        return pnl

    def get_unrealized_pnl(self,
                           date: Optional[Date] = None,
                           universe: Optional[Universe] = None,
                           account: Optional[AccountTypes] = None,
                           company: CompanyTypes = None,
                           account_types: Sequence[Account.AccountType] = None) -> PnLData:
        """
        Compute the unrealized PnL for an account.

        :param account: Account identifier (id or Account)
        :param universe: Universe, the current universe
        :param date: Date, used to get the FxPosition objects (you can use this to get unrealized PnLs as of
            a certain time in history for the account)
        :param company: CompanyTypes, if provided, the company to get positions for
        :param account_types, what types of accounts to get PnL for.
        :return: float, Unrealized PnL in the account currency
        """
        if date is None:
            if not universe:
                raise ValueError("you must supply either a date or a universe")
            date = universe.date

        positions, domestic = _get_positions(account=account, company=company, account_types=account_types, date=date)

        # If a universe wasn't provided, make one.
        if not universe:
            universe = self._universe_provider.make_cntr_currency_universe(
                domestic=company.currency, ref_date=date, bypass_errors=True)

        pnl = self._pnl_calculator.calc_unrealized_pnl_of_positions(spot_fx_cache=universe,
                                                                    positions=positions, currency=domestic)

        fxforwards = _get_fxforward_positions(account=account, company=company, account_types=account_types, date=date)
        forward_pnl = self._pnl_calculator.calc_unrealized_pnl_of_fxforwards(fx_forwards=fxforwards,
                                                                             universe=universe,
                                                                             currency=domestic)

        return PnLData(fxspot_pnl=pnl, fxforward_pnl=forward_pnl,
                       domestic=company.currency if company else account.company.currency)

    def get_approximate_forwards_theta(self,
                                       date: Optional[Date] = None,
                                       universe: Optional[Universe] = None,
                                       account: Optional[AccountTypes] = None,
                                       company: CompanyTypes = None,
                                       account_types: Sequence[Account.AccountType] = None):
        if not account and not company:
            raise ValueError("you must supply either an account or a company")
        domestic = company.currency if company else account.company.currency
        fxforwards = _get_fxforward_positions(account=account, company=company, account_types=account_types, date=date)
        return self._pnl_calculator.calc_approximate_theta_of_fxforwards(fx_forwards=fxforwards,
                                                                         universe=universe,
                                                                         currency=domestic)
