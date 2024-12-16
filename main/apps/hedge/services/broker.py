from abc import ABCMeta, abstractmethod
from typing import Optional, Union, Dict, List, Tuple

import numpy as np

from hdlib.Hedge.Cash.CashPositions import VirtualFxPosition

from hdlib.Core.FxPair import FxPair as FxPairHDL
from main.apps.account.models import CompanyTypes, Account, Company
from main.apps.broker.models import BrokerAccount

import logging

from main.apps.currency.models import FxPair, Currency

from main.apps.margin.services.broker_margin_service import BrokerMarginServiceInterface, BrokerMarginRequirements
from main.apps.oems.services.order_service import OrderService, BacktestOrderService

logger = logging.getLogger(__name__)


class BrokerAccountSummary:
    def __init__(self,
                 account_type: str,
                 cushion: float,
                 look_ahead_next_change: float,
                 accrued_cash: float,
                 available_funds: float,
                 buying_power: float,
                 equity_with_loan_value: float,
                 excess_liquidity: float,
                 full_available_funds: float,
                 full_excess_liquidity: float,
                 full_init_margin_req: float,
                 full_maint_margin_req: float,
                 gross_position_value: float,
                 init_margin_req: float,
                 look_ahead_available_funds: float,
                 look_ahead_excess_liquidity: float,
                 look_ahead_init_margin_req: float,
                 look_ahead_maint_margin_req: float,
                 maint_margin_req: float,
                 net_liquidation: float,
                 sma: float,
                 total_cash_value: float
                 ):
        """
        Create a BrokerAccountSummary object. For some definitions, see
        https://guides.interactivebrokers.com/tws/usersguidebook/realtimeactivitymonitoring/available_for_trading.htm
        https://guides.interactivebrokers.com/tws/usersguidebook/realtimeactivitymonitoring/balances.htm

        ***Important definitions***:

        Available funds: This value tells what you have available for trading.
            Securities: Equal to (Equity with Loan Value) - (Initial margin).
            Commodities: Equal to (Net Liquidation Value) - (Initial Margin).

        Excess liquidity: This value shows your margin cushion, before liquidation.
            Securities: Equal to (Equity with Loan Value) - (Maintenance margin).
            Commodities: Equal to (Net Liquidation value) - (Maintenance margin).

        Look ahead available funds: This value reflects your available funds at the next margin change. The next
            change is displayed in the Look Ahead Next Change field.
            Equal to (Equity with loan value) - (look ahead initial margin).

        Buying power:
            Cash Account: Min{ (Equity with Loan Value), (Previous Day Equity with Loan Value) } - (Initial Margin)
            Standard Margin Account:
                Min{ Equity with Loan Value, Previous Day Equity with Loan Value } - 4 * (Initial Margin)

        Gross Position Value: Equals the sum of the absolute value of all positions except cash, index futures and
            US treasuries.

        For some things on accrued cash, see see
        https://www.interactivebrokers.com/en/pricing/pricing-calculations-int.php
        """
        self.account_type = account_type
        self.cushion = cushion
        self.look_ahead_next_change = look_ahead_next_change
        self.accrued_cash = accrued_cash  #
        self.available_funds = available_funds  # Equity with Loan - Initial margin (or NLV - Initial margin, for CM)
        self.buying_power = buying_power
        self.equity_with_loan_value = equity_with_loan_value
        self.excess_liquidity = excess_liquidity
        self.full_available_funds = full_available_funds
        self.full_excess_liquidity = full_excess_liquidity
        self.full_init_margin_req = full_init_margin_req
        self.full_maint_margin_req = full_maint_margin_req
        self.gross_position_value = gross_position_value
        self.init_margin_req = init_margin_req
        self.look_ahead_available_funds = look_ahead_available_funds
        self.look_ahead_excess_liquidity = look_ahead_excess_liquidity
        self.look_ahead_init_margin_req = look_ahead_init_margin_req
        self.look_ahead_maint_margin_req = look_ahead_maint_margin_req
        self.maint_margin_req = maint_margin_req
        self.net_liquidation = net_liquidation
        self.sma = sma  # Special Memorandum Account - see https://ibkr.info/node/66
        self.total_cash_value = total_cash_value

    @staticmethod
    def from_dict(broker_account_summary: dict) -> Optional['BrokerAccountSummary']:
        if broker_account_summary is None:
            return None
        if len(broker_account_summary) == 0:
            return None
        try:
            def as_float(name: str):
                return float(broker_account_summary['flat'][name])

            def as_int(name: str):
                return int(broker_account_summary['flat'][name])

            def as_str(name: str):
                return str(broker_account_summary['flat'][name])

            return BrokerAccountSummary(account_type=as_str("AccountType"),
                                        cushion=as_float("Cushion"),
                                        look_ahead_next_change=as_float("LookAheadNextChange"),
                                        accrued_cash=as_float("AccruedCash"),
                                        available_funds=as_float("AvailableFunds"),
                                        buying_power=as_float("BuyingPower"),
                                        equity_with_loan_value=as_float("EquityWithLoanValue"),
                                        excess_liquidity=as_float("ExcessLiquidity"),
                                        full_available_funds=as_float("FullAvailableFunds"),
                                        full_excess_liquidity=as_float("FullExcessLiquidity"),
                                        full_init_margin_req=as_float("FullInitMarginReq"),
                                        full_maint_margin_req=as_float("FullMaintMarginReq"),
                                        gross_position_value=as_float("GrossPositionValue"),
                                        init_margin_req=as_float("InitMarginReq"),
                                        look_ahead_available_funds=as_float("LookAheadAvailableFunds"),
                                        look_ahead_excess_liquidity=as_float("LookAheadExcessLiquidity"),
                                        look_ahead_init_margin_req=as_float("LookAheadInitMarginReq"),
                                        look_ahead_maint_margin_req=as_float("LookAheadMaintMarginReq"),
                                        maint_margin_req=as_float("MaintMarginReq"),
                                        net_liquidation=as_float("NetLiquidation"),
                                        sma=as_float("SMA"),
                                        total_cash_value=as_float("TotalCashValue"),
                                        )
        except Exception as ex:
            logger.error(f"Exception in creating BrokerAccountSummary: {ex}")
            raise ex


class BrokerServiceInterface(BrokerMarginServiceInterface, metaclass=ABCMeta):
    @abstractmethod
    def get_broker_for_company(self, company: Company, account_type: Account.AccountType) -> Optional[BrokerAccount]:
        pass

    @abstractmethod
    def get_broker_account_name_for_company(self, company: Company,
                                            account_type: Account.AccountType) -> Optional[str]:
        pass

    @abstractmethod
    def get_broker_account_names(self, company: Company) -> List[str]:
        pass

    @abstractmethod
    def get_broker_account_summary(self, company: CompanyTypes,
                                   account_type: Account.AccountType) -> Optional[BrokerAccountSummary]:
        pass

    @abstractmethod
    def get_account_positions_by_broker(self, company: Company) -> Dict[BrokerAccount, dict]:
        pass

    @abstractmethod
    def get_cash_holdings(self,
                          company: Optional[Company] = None,
                          account: str = "") -> Tuple[Dict[BrokerAccount, Dict[Currency, float]], Dict[BrokerAccount, Dict[Currency, float]]]:
        """
        Get the cash holdings of a company, grouped by broker account.
        """
        pass

    @abstractmethod
    def get_account_positions(self,
                              company: CompanyTypes,
                              account_type: Account.AccountType) -> Optional[dict]:
        pass

    @abstractmethod
    def get_broker_account_positions(self, broker_account: Union[str, BrokerAccount]) -> List[VirtualFxPosition]:
        pass

    @abstractmethod
    def run_what_if_order(self, broker_account: Union[str, BrokerAccount],
                          fxpair: Union[str, FxPairHDL],
                          amount: float):
        pass

    @abstractmethod
    def submit_order(self,broker_account: Union[str, BrokerAccount], fxpair: Union[str, FxPairHDL], amount: float):
        pass

    @abstractmethod
    def cancel_order(self, order):
        pass

    @abstractmethod
    def get_all_broker_account_data(self) -> Dict[BrokerAccount, BrokerAccountSummary]:
        pass

    @abstractmethod
    def get_allsummary_broker_account_data(self) -> dict:
        pass


class BrokerService(BrokerServiceInterface):
    def __init__(self):
        pass

    def get_broker_margin_summary(self, company: Company,
                                  account_type: Account.AccountType) -> BrokerMarginRequirements:
        summary = self.get_broker_account_summary(company=company,
                                                  account_type=account_type)
        if not summary:
            return BrokerMarginRequirements(init_margin=0, maint_margin=0, excess_liquidity=0, additional_cash=0,
                                            equity_with_loan_value=0)
        maint_margin = summary.full_maint_margin_req
        init_margin = summary.full_init_margin_req
        excess_liquidity = summary.full_excess_liquidity
        # TODO - This is copied from Nate's example. Check if available funds is actually what we need.
        # TODO - I think available funds is the funds available for withdrawal. Which is different from available cash
        additional_cash = summary.available_funds
        return BrokerMarginRequirements(init_margin=init_margin,
                                        maint_margin=maint_margin,
                                        excess_liquidity=excess_liquidity,
                                        additional_cash=additional_cash,
                                        equity_with_loan_value=summary.equity_with_loan_value)

    def get_broker_for_company(self,
                               company: CompanyTypes,
                               account_type: Account.AccountType) -> Optional[BrokerAccount]:
        if account_type == Account.AccountType.DEMO:
            account_types = (BrokerAccount.AccountType.PAPER,)
        else:
            account_types = (BrokerAccount.AccountType.LIVE,)

        broker_accounts = BrokerAccount.get_accounts_for_company(company=company, account_types=account_types)
        if broker_accounts:
            return broker_accounts[0]
        return None

    def get_broker_account_name_for_company(self,
                                            company: CompanyTypes,
                                            account_type: Account.AccountType) -> Optional[str]:
        broker_account = self.get_broker_for_company(company=company, account_type=account_type)
        if broker_account:
            return broker_account.broker_account_name
        return None

    def get_broker_account_names(self, company: Company) -> List[str]:
        return BrokerAccount.objects.filter(company=company)

    def get_broker_account_summary(self,
                                   company: CompanyTypes,
                                   account_type: Account.AccountType) -> Optional[BrokerAccountSummary]:
        try:
            return BrokerAccountSummary.from_dict(self._call_for_account(company, account_type, "get_account_summary"))
        except Exception:
            return None

    def get_margin_for_company(self,
                               company: CompanyTypes,
                               account_type: Account.AccountType):
        """ Get the margin parameters for a company. Returns None upon failure. """
        summary = self.get_broker_account_summary(company=company, account_type=account_type)
        if summary:
            return summary.maint_margin_req
        return None

    def get_account_positions_by_broker(self, company: Company) -> Dict[BrokerAccount, dict]:
        # NOTE(Nate): This will have to be revisited when we are actually using multiple brokers.
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()
        positions = {}

        # Get live accounts.
        live_broker_account = self.get_broker_for_company(company=company, account_type=Account.AccountType.LIVE)
        if live_broker_account:
            positions[live_broker_account] = api.get_positions(live_broker_account.broker_account_name)
        # Get demo accounts.
        demo_broker_account = self.get_broker_for_company(company=company, account_type=Account.AccountType.DEMO)
        if demo_broker_account:
            positions[demo_broker_account] = api.get_positions(demo_broker_account.broker_account_name)

        return positions

    def get_cash_holdings(self,
                          company: Optional[Company] = None,
                          account: str = "") -> Tuple[Dict[BrokerAccount, Dict[Currency, float]],
                                                      Dict[BrokerAccount, Dict[Currency, float]]]:
        """
        Get the cash holdings of a company, grouped by broker account.
        """
        if company is None and len(account) == 0:
            raise ValueError(f"either company or account must be provided")
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()

        accrued_cash, cash_balance = {}, {}

        broker_name = account  # May be empty.
        if 0 < len(account):
            broker_account = BrokerAccount.get_account(broker_name)
        else:
            broker_account = self.get_broker_for_company(company=company, account_type=Account.AccountType.LIVE)
            if broker_account:
                broker_name = broker_account.broker_account_name

        # Get live accounts.
        if broker_account:
            logger.debug(f"Found broker account with name '{broker_name}' for company {company}.")

            all_values = api.get_account_values()
            all_values = all_values[broker_name]

            accrued_cash_for_broker, cash_balance_for_broker = {}, {}
            for currency_str, values in all_values.items():
                try:
                    currency = Currency.get_currency(currency_str)
                    if 'AccruedCash' in values:
                        cash = values['AccruedCash']
                        if cash != 0.0:
                            accrued_cash_for_broker[currency] = cash
                    if 'CashBalance' in values:
                        cash = values['CashBalance']
                        if cash != 0.0:
                            cash_balance_for_broker[currency] = cash
                except Exception:
                    logger.error(f"Currency with string '{currency_str}' cannot be mapped to a db Currency object.")
            if 0 < len(accrued_cash_for_broker):
                accrued_cash[broker_account] = accrued_cash_for_broker
            if 0 < len(cash_balance_for_broker):
                cash_balance[broker_account] = cash_balance_for_broker
        else:
            logger.debug(f"Could not find broker for company {company}.")

        logger.debug(f"Finished getting cash balances for company {company}.")
        return cash_balance, accrued_cash


    def get_account_positions(self,
                              company: CompanyTypes,
                              account_type: Account.AccountType) -> Optional[dict]:
        return self._call_for_account(company, account_type, "get_positions")

    def get_broker_account_positions(self, broker_account: Union[str, BrokerAccount]) -> List[VirtualFxPosition]:
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()
        name = broker_account.broker_account_name if isinstance(broker_account, BrokerAccount) else broker_account
        positions = api.get_positions(account=name).get(name, [])

        virtual_fx_positions = []
        for position in positions:
            fx = VirtualFxPosition(fxpair=FxPair.get_pair(position["FxPair"]).to_FxPairHDL(),
                                   amount=position["position"],
                                   ave_price=position["avgCost"])
            virtual_fx_positions.append(fx)
        return virtual_fx_positions

    def run_what_if_order(self,
                          broker_account: Union[str, BrokerAccount],
                          fxpair: Union[str, FxPairHDL],
                          amount: float):
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()

        action = "BUY" if 0 < amount else "SELL"
        fxname = fxpair if isinstance(fxpair, str) else f"{fxpair.base}{fxpair.quote}"
        broker_name = broker_account if isinstance(broker_account, str) else broker_account.broker_account_name
        return api.place_what_if_fx_trade(fx_pair_name=fxname,
                                          action=action,
                                          amount=np.abs(amount),
                                          account=broker_name)

    def submit_order(self, broker_account: Union[str, BrokerAccount], fxpair: Union[str, FxPairHDL], amount: float):
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()

        action = "BUY" if 0 < amount else "SELL"
        fxname = fxpair if isinstance(fxpair, str) else f"{fxpair.base}{fxpair.quote}"
        broker_name = broker_account if isinstance(broker_account, str) else broker_account.broker_account_name
        return api.place_trade(fx_pair_name=fxname,
                               action=action,
                               amount=np.abs(amount),
                               account=broker_name)

    def cancel_order(self, order):
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        return TwsApi().cancel_order(order)

    def get_all_broker_account_data(self) -> Dict[BrokerAccount, BrokerAccountSummary]:
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()
        all_account_summaries = api.get_account_summary()

        summaries_out = {}
        for broker_account, summary in all_account_summaries.items():
            if broker_account != "All":
                summaries_out[broker_account] = BrokerAccountSummary.from_dict(summary)
        return summaries_out

    def get_allsummary_broker_account_data(self) -> dict:
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        api = TwsApi()
        return api.get_allsummary()

    def _call_for_account(self, company: CompanyTypes, account_type: Account.AccountType, method_name: str, **kwargs):
        from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
        broker_account_name = self.get_broker_account_name_for_company(company=company,
                                                                       account_type=account_type)
        logger.debug(f"For company {company}, calling function for account (function = {method_name}).")
        if broker_account_name:
            logger.debug(f"Broker account name found to be {broker_account_name}.")
            api = TwsApi()
            return getattr(api, method_name)(account=broker_account_name, **kwargs)
        logger.debug(f"Cannot call function, no broker account name could be found for company {company}.")
        return None


class BacktestingBrokerService(BrokerService):

    def __init__(self, order_service: BacktestOrderService):
        self._order_service = order_service
    def get_broker_account_summary(self, company: CompanyTypes, account_type: Account.AccountType) -> Optional[BrokerAccountSummary]:
        return None

    def get_account_positions_by_broker(self, company: Company) -> Dict[BrokerAccount, dict]:
        return {}

    def get_cash_holdings(self, company: Optional[Company] = None, account: str = "") -> Tuple[Dict[BrokerAccount, Dict[Currency, float]], Dict[BrokerAccount, Dict[Currency, float]]]:
        broker_account = company.broker_accounts.first()
        if not broker_account:
            return {}, {}
        return {broker_account: self._order_service.cash_positions}, {broker_account: {}}

    def get_account_positions(self, company: CompanyTypes, account_type: Account.AccountType) -> Optional[dict]:
        return {}

    def get_broker_account_positions(self, broker_account: Union[str, BrokerAccount]) -> List[VirtualFxPosition]:
        return []

    def run_what_if_order(self, broker_account: Union[str, BrokerAccount], fxpair: Union[str, FxPairHDL],
                          amount: float):
        return {}

    def submit_order(self, broker_account: Union[str, BrokerAccount], fxpair: Union[str, FxPairHDL], amount: float):
        return {}

    def cancel_order(self, order):
        return {}

    def get_all_broker_account_data(self) -> Dict[BrokerAccount, BrokerAccountSummary]:
        return {}

    def get_allsummary_broker_account_data(self) -> dict:
        return {}

    def get_broker_margin_summary(self, company: Company,
                                  account_type: Account.AccountType) -> BrokerMarginRequirements:
        return BrokerMarginRequirements(init_margin=0,
                                        maint_margin=0,
                                        excess_liquidity=1e9,
                                        additional_cash=1e9,
                                        equity_with_loan_value=0)
