import asyncio
import threading
from contextlib import contextmanager
from typing import Sequence, Iterable, Tuple

from django.conf import settings
from ib_insync import *

import logging

from main.apps.ibkr.services import TWSClientID
from main.apps.currency.models.fxpair import FxPair

logger = logging.getLogger(__name__)


class IBConnection:
    lock = threading.RLock()
    ib = IB()
    client_id_helper = TWSClientID(min_client_id=5, max_client_id=32)

    @classmethod
    @contextmanager
    def client(cls):

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cls.lock.acquire()
        if not cls.ib.isConnected():
            if settings.IB_GATEWAY_USE_STATIC_CLIENT_ID:
                cls.ib.connect(settings.IB_GATEWAY_URL, settings.IB_GATEWAY_PORT, settings.IB_GATEWAY_CLIENT_ID)
            else:
                client_id: int = cls.client_id_helper.get_client_id()
                cls.ib.connect(settings.IB_GATEWAY_URL, settings.IB_GATEWAY_PORT, client_id)
        cls.lock.release()

        yield cls.ib

    @classmethod
    def disconnect(cls):
        cls.lock.acquire()
        if cls.ib.isConnected():
            cls.ib.disconnect()
            if not settings.IB_GATEWAY_USE_STATIC_CLIENT_ID:
                cls.client_id_helper.release_client_id()
        cls.lock.release()


class TwsApi:
    """
    Connector class for interacting with IBKR TWS API using linear programming, this is an extension of ib_insync
    package.

    See documentation:
    *  https://ib-insync.readthedocs.io/api.html

    """

    def __del__(self):
        IBConnection.disconnect()

    def get_contract(self, type: str, symbol: str, **kwargs) -> Contract:
        """
        Get an instance of a contract - accepted types are:
            stock - Stock
            option - Option
            future - Future
            cont_future - Continuous Future Contract
            forex - Forex
            index - Index
            cfd - Contract For Difference
            commodity - Commodity
            bond - Bond
            future_option - Future Option
            mutual_fund - Mutual Fund
            warrant - Warrant
            bag - Bag
            crypto - Crypto
        """
        if type == "stock":
            return Stock(symbol)
        if type == "option":
            return Option(symbol)
        if type == "future":
            return Future(**kwargs)
        if type == "cont_future":
            return ContFuture(symbol)
        if type == "forex":
            return Forex(symbol)
        if type == "index":
            return Index(symbol)
        if type == "cfd":
            return CFD(symbol)
        if type == "commodity":
            return Commodity(symbol)
        if type == "bond":
            return Bond(**kwargs)
        if type == "future_option":
            return FuturesOption(symbol)
        if type == "mutual_fund":
            return MutualFund(**kwargs)
        if type == "warrant":
            return Warrant(**kwargs)
        if type == "bag":
            return Bag(**kwargs)
        if type == "crypto":
            return Crypto(symbol)

    def get_client(self) -> IB:
        with IBConnection.client() as ib:
            return ib

    def qualify_contracts(self, contracts: Iterable):
        with IBConnection.client() as ib:
            return ib.qualifyContracts(*contracts)

    def req_contract_details(self, contract: Contract):
        with IBConnection.client() as ib:
            ib: IB
            return ib.reqContractDetails(contract=contract)

    def get_managed_accounts(self) -> Sequence[str]:
        """ List of account names. """
        with IBConnection.client() as ib:
            return ib.managedAccounts()

    def get_account_summary(self, account: str = "") -> dict:
        """ Returns a dictionary of accounts and their summary values. """
        with IBConnection.client() as ib:
            account_summary_response = ib.accountSummary(account)
            all_data = self._convert_account_values_to_dict(values=account_summary_response)
            if len(account) == 0:
                return all_data
            else:
                return all_data.get(account, {})

    def get_allsummary(self) -> dict:
        with IBConnection.client() as ib:
            data = {}
            for account_value in ib.accountSummary("All"):
                # These do not have floats as their value.
                if account_value.tag == "Currency" or account_value.tag == "AccountOrGroup" \
                    or account_value.tag == "RealCurrency":
                    continue
                if account_value.tag not in data:
                    data[account_value.tag] = []
                try:
                    data[account_value.tag].append((float(account_value.value), account_value.currency))
                except Exception:
                    pass
            return data

    def get_account_values(self, account: str = "") -> dict:
        """ Returns a dictionary of accounts and their values """
        with IBConnection.client() as ib:
            logger.debug(f"Getting account values for account {account}")
            accounts_values_response = ib.accountValues(account)
            return self._convert_account_values_to_dict(values=accounts_values_response)

    def get_positions(self, account=""):
        # TODO: Use the company.
        with IBConnection.client() as ib:
            positions_response = ib.positions(account)
            return self._convert_positions_to_dict(positions_response)

    def place_what_if_fx_trade(self, account: str, action: str, fx_pair_name: str, amount: float):
        """
        action: str, "BUY" or "SELL"
        """
        if len(account) == 0:
            raise ValueError("must specify an account to place a what-if trade")
        with IBConnection.client() as ib:
            order = MarketOrder(action=action, totalQuantity=amount)
            order.account = account
            return ib.whatIfOrder(contract=Forex(fx_pair_name), order=order)

    def place_trade(self, account: str, action: str, fx_pair_name: str, amount: float) -> Tuple[Trade, Order]:
        with IBConnection.client() as ib:
            order = MarketOrder(action=action, totalQuantity=amount)
            order.account = account
            return ib.placeOrder(contract=Forex(fx_pair_name), order=order), order

    def cancel_order(self, order: Order):
        with IBConnection.client() as ib:
            return ib.cancelOrder(order)

    def pnl_single(self, account: str = ""):
        with IBConnection.client() as ib:
            return ib.pnlSingle(account=account)

    def test(self, account: str = ""):
        with IBConnection.client() as ib:
            contract = Contract.create(secType="CASH", pair="EURUSD")
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min',
                whatToShow='MIDPOINT',
                useRTH=False,
                formatDate=1)
            return util.df(bars)

    # ====================================================================================================
    #  Private helper functions.
    # ====================================================================================================

    def _convert_account_values_to_dict(self, values: Sequence[AccountValue]) -> dict:
        """ Helper method to convert List[AccountValue] to dict """
        output = {}
        for value in values:
            output.setdefault(value.account, {}).setdefault(value.currency, {})[value.tag] = value.value
            output.setdefault(value.account, {}).setdefault("flat", {})[value.tag] = value.value
        return output

    def _convert_positions_to_dict(self, positions: Sequence[Position]):
        """ Helper method to convert List[Position] to dict """
        output = {}
        for position in positions:
            if position.account not in output:
                output[position.account] = []
            _position = {
                "avgCost": position.avgCost,
                "position": position.position,
                "contract": position.contract,
                "FxPair": FxPair.objects.filter(
                    base_currency__mnemonic=position.contract.symbol,
                    quote_currency__mnemonic=position.contract.currency
                ).first()
            }
            output[position.account].append(_position)
        return output
