import abc
from typing import List, Optional, Tuple, Iterable, Dict
import numpy as np

from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.Hedge.Fx.HedgeAccount import CashExposures_Cached, CashExposures
from hdlib.Instrument.CashFlow import CashFlow as CashFlowHDL
from hdlib.Instrument.CashFlow import CashFlows as CashFlowsHDL

from main.apps.account.models import Company
from main.apps.account.models.account import Account, AccountTypes
from main.apps.account.models.cashflow import CashFlow
from main.apps.currency.models.currency import Currency, CurrencyTypes
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.hedge.models.hedgesettings import HedgeAccountSettings_DB, HedgeSettings


class CashFlowProviderInterface(abc.ABC):
    """
    Service responsible for providing cashflows, and aggregating them across all ways in which cashflows
    are defined (raw, recurring, installments, etc.)
    """

    @abc.abstractmethod
    def get_active_cashflows(self,
                             start_date: Date,
                             account: Account,
                             inclusive: bool = False,
                             include_end: bool = False,
                             max_days_away: Optional[int] = None,
                             max_date_in_future: Optional[Date] = None,
                             exclude_unknown_on_ref_date: bool = False,
                             currencies: Iterable[Currency] = None) -> Iterable[CashFlowHDL]:
        """
        Get "active" cashflows for an account, ie those that have not already been paid
        :param start_date: Date, the reference date (only cashflows occurring on or after this date are considered)
        :param account: AccountId or Account
        :param inclusive: bool, if true, include cashflows occurring on ref_date, else only those strictly after
        :param include_end: bool, if true, include cashflows that occur exatly on the end date.
        :param max_days_away: int (optional), if supplied, ignore all cashflows that are more than this many
            days from the ref_date
        :param max_date_in_future: Date (optional), if supplied ignore all cashflows after this date
        :param exclude_unknown_on_ref_date: bool, if true, exclude all cashflows that were not created by the ref_date,
            this flag is for historical testing / reporting purposes, since hedges only knew cashflows that existed
            at the time of the hedge
        :param currencies: Iterable of currency ids or objects (optional), if supplied only return matching currencies
        :return: iterable of CashFlow objects
        """
        raise NotImplementedError()

    def get_active_cashflows_for_company(self,
                                         company: Company,
                                         start_date: Date,
                                         inclusive: bool = False,
                                         max_days_away: Optional[int] = None,
                                         max_date_in_future: Optional[Date] = None,
                                         exclude_unknown_on_ref_date: bool = False,
                                         currencies: Iterable[Currency] = None) -> Dict[Account, List[CashFlowHDL]]:
        cashflows = {}
        for account in company.acct_company.all():
            if not account.is_active:
                continue
            cashflows[account] = list(
                self.get_active_cashflows(start_date=start_date,
                                          account=account,
                                          inclusive=inclusive,
                                          max_days_away=max_days_away,
                                          max_date_in_future=max_date_in_future,
                                          exclude_unknown_on_ref_date=exclude_unknown_on_ref_date,
                                          currencies=currencies))
        return cashflows

    def get_cash_exposures(self,
                           date: Date,
                           settings: HedgeAccountSettings_DB,
                           inclusive: bool = False,
                           ignore_domestic: bool = True,
                           include_forwards: bool = False) -> CashExposures:
        """ Retrieve cash exposures in the counter-currency convention """

        flows = self.get_active_cashflows(start_date=date, account=settings.account,
                                          inclusive=inclusive)

        # NOTE(Nate): We used to create a dictionary that could only hold currencies from your settings, but
        #   your cashflows are your cashflows, even if the currency is not in your allowed currencies.
        #   That being said, it is probably an error if you have a cashflow that is not in your settings.currencies
        #   list.
        flows_by_currency = {}
        for cashflow in flows:
            currency = cashflow.currency
            if ignore_domestic and currency.get_mnemonic() == settings.domestic.get_mnemonic():
                continue
            flows_by_currency.setdefault(cashflow.currency, []).append(cashflow)

        if include_forwards:
            # Add cashflows from forward positions.
            forwards = FxForwardPosition.get_forwards_for_account(current_time=date, account=settings.account)
            for fwd in forwards:
                for cashflow in fwd.to_cashflows():
                    currency = cashflow.currency
                    if ignore_domestic and currency.get_mnemonic() == settings.domestic.get_mnemonic():
                        continue
                    flows_by_currency.setdefault(cashflow.currency, []).append(cashflow)

        return CashExposures_Cached(date=date, cashflows=flows_by_currency, settings=settings)

    def get_cash_exposures_for_account(self, time: Date, account: AccountTypes) -> CashExposures:
        """
        Get the cash exposures for a particular account as of some time.
        """
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account_)
        settings = HedgeSettings.get_hedge_account_settings_hdl(account=account_)
        return self.get_cash_exposures(date=time, settings=settings, include_forwards=True)

    def get_cashflows_by_rolloff_date(self,
                                      start_date: Date,
                                      account: Account,
                                      inclusive: bool = False,
                                      max_days_away: Optional[int] = None,
                                      max_date_in_future: Optional[Date] = None,
                                      exclude_unknown_on_ref_date: bool = False,
                                      currencies: Iterable[CurrencyTypes] = None) -> Dict[Date, List[CashFlowHDL]]:
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)
        cashflows = CashFlowProviderService().get_active_cashflows(
            start_date=start_date,
            account=account,
            inclusive=inclusive,
            max_days_away=max_days_away,
            max_date_in_future=max_date_in_future,
            exclude_unknown_on_ref_date=exclude_unknown_on_ref_date,
            currencies=currencies
        )
        # Organize cashflows by when they roll off (i.e. the day on which they are paid).
        cashflows_by_rolloff_date = {}
        for cashflow in cashflows:
            pay_date = cashflow.pay_date
            if pay_date not in cashflows_by_rolloff_date:
                cashflows_by_rolloff_date[pay_date] = []
            cashflows_by_rolloff_date[pay_date].append(cashflow)
        return cashflows_by_rolloff_date

    def get_projected_raw_cash_exposures(self,
                                         account: Account,
                                         start_date: Date,
                                         end_date: Date,
                                         ) -> List[Tuple[Date, List[Tuple[Currency, float]]]]:
        """
        Returns a right continuous representation of the cash exposures (raw cash values, undiscounted and not Fx'ed
        by the forward curve).
        You have no cash exposure to a cashflow on the day that it rolls off.
        """
        dc = DayCounter_HD()
        settings = HedgeSettings.get_hedge_account_settings_hdl(account=account)
        effective_max_days = dc.days_between(start_date, end_date) + settings.max_horizon
        cashflows_by_rolloff = self.get_cashflows_by_rolloff_date(start_date=start_date,
                                                                  account=account,
                                                                  max_days_away=effective_max_days)
        if len(cashflows_by_rolloff) == 0:
            return []

        # Compute initial cash exposure.
        running_cash_exposures = {}
        for date, cashflows in cashflows_by_rolloff.items():
            for cashflow in cashflows:
                currency = cashflow.currency
                if start_date < cashflow.pay_date:
                    running_cash_exposures[currency] = running_cash_exposures.get(currency, 0) + cashflow.amount

        # In the first pass, compute the amount of cash in each currency that has rolled off.
        cash_exposures = [(start_date, [(currency, amount) for currency, amount in running_cash_exposures.items()])]
        # Add first entry

        for date, cashflows in cashflows_by_rolloff.items():
            if end_date < date:
                break
            # Subtract paid cash amounts
            for cashflow in cashflows:
                amount = running_cash_exposures[cashflow.currency]
                amount -= cashflow.amount
                if np.abs(amount) < 0.001:
                    amount = 0
                running_cash_exposures[cashflow.currency] = amount
            cash_exposures.append((date, [(currency, amount) for currency, amount in running_cash_exposures.items()]))

        return cash_exposures

    def get_projected_raw_cash_exposures_ts(self,
                                            account: Account,
                                            start_date: Date,
                                            end_date: Date) -> Tuple[List[Date], Dict[Currency, List[float]]]:
        cash_exposures = self.get_projected_raw_cash_exposures(account=account,
                                                               start_date=start_date,
                                                               end_date=end_date)
        # Initialize lists
        dates = []
        time_series = {}
        for currency, _ in cash_exposures[0][1]:
            time_series[currency] = []

        # Reshape.
        for date, exposures in cash_exposures:
            dates.append(date)
            for currency, amount in exposures:
                time_series[currency].append(amount)

        return dates, time_series

    def get_active_hdl_cashflows_by_currency(self,
                                             ref_date: Date,
                                             account: Account,
                                             inclusive: bool = False,
                                             max_days_away: Optional[int] = None,
                                             max_date_in_future: Optional[Date] = None,
                                             exclude_unknown_on_ref_date: bool = False,
                                             currencies: Iterable[CurrencyTypes] = None
                                             ) -> Dict[Currency, CashFlowsHDL]:
        """
        Get "active" cashflows for an account, ie those that have not already been paid.
        :param ref_date: Date, the reference date (only cashflows occuring on or after this date are considered)
        :param account: AccountId or Account
        :param inclusive: bool, if true, include cashflows occurring on ref_date, else only those strictly after
        :param max_days_away: int (optional), if supplied, ignore all cashflows that are more than this many
            days from the ref_date
        :param max_date_in_future: Date (optional), if supplied ignore all cashflows after this date
        :param exclude_unknown_on_ref_date: bool, if true, exclude all cashflows that were not created by the ref_date,
            this flag is for historical testing / reporting purposes, since hedges only knew cashflows that existed
            at the time of the hedge
        :param currencies: Iterable of currency ids or objects (optional), if supplied only return matching currencies
        :return: Dictionary, where keys are the Currency objects, and values are CashFlowsHDL objects (ie sequences
            of SORTED cashflows per currency)
        """
        flows = self.get_active_cashflows(start_date=ref_date, account=account, inclusive=inclusive,
                                          max_days_away=max_days_away,
                                          max_date_in_future=max_date_in_future,
                                          exclude_unknown_on_ref_date=exclude_unknown_on_ref_date,
                                          currencies=currencies)
        out = {}
        for flow in flows:
            currency = flow.currency
            if currency not in out:
                out[currency] = []

            out[currency].append(flow)

        for currency in out.keys():
            out[currency] = CashFlowsHDL(cashflows=out[currency])

        return out


class CashFlowProviderService(CashFlowProviderInterface):
    """
    DB implementation of CashFlowProviderInterface
    """

    def get_active_cashflows(self,
                             start_date: Date,
                             account: Account,
                             inclusive: bool = False,
                             include_end: bool = True,
                             max_days_away: Optional[int] = None,
                             max_date_in_future: Optional[Date] = None,
                             exclude_unknown_on_ref_date: bool = False,
                             currencies: Iterable[CurrencyTypes] = None,
                             skip_less_than_ref_date: bool = False) -> Iterable[CashFlowHDL]:
        return CashFlow.get_active_cashflows(start_date=start_date,
                                             account=account,
                                             inclusive=inclusive,
                                             include_end=include_end,
                                             max_days_away=max_days_away,
                                             max_date_in_future=max_date_in_future,
                                             exclude_unknown_on_ref_date=exclude_unknown_on_ref_date,
                                             currencies=currencies,
                                             skip_less_than_ref_date=skip_less_than_ref_date)
