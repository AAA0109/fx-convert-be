from abc import abstractmethod

from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.FxPairInterface import FxPairInterface


class AccountHedgeResultInterface(object):
    """
    Abstract base class for objects that can be used to store the results of an account hedge request.
    """

    @abstractmethod
    def set_filled_amount(self, filled_amount: float):
        raise NotImplementedError

    @abstractmethod
    def set_avg_price(self, avg_price: float):
        raise NotImplementedError

    @abstractmethod
    def set_commissions(self, commission: float, cntr_commission: float):
        raise NotImplementedError

    @abstractmethod
    def set_realized_pnl_quote(self, pnl_quote: float):
        raise NotImplementedError

    @abstractmethod
    def set_realized_pnl_domestic(self, pnl_domestic: float):
        raise NotImplementedError

    @abstractmethod
    def get_request(self) -> 'AccountHedgeRequestInterface':
        """ Get the request that this result belongs to. """
        raise NotImplementedError

    @abstractmethod
    def get_filled_amount(self) -> float:
        """ Get the total filled amount. """
        raise NotImplementedError

    @abstractmethod
    def get_total_price(self) -> float:
        """ Get the total price, the filled amount times the average price. """
        raise NotImplementedError

    @abstractmethod
    def get_pnl_quote(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_pnl_domestic(self) -> float:
        raise NotImplementedError


class BasicAccountHedgeResult(AccountHedgeResultInterface):
    """
    A basic implementation of the AccountHedgeResultInterface that just stores everything internally.
    """
    def __init__(self, request: 'AccountHedgeRequestInterface'):
        self.request = request
        self.filled_amount = 0
        self.avg_price = 0
        self.commission = 0
        self.cntr_commission = 0
        self.pnl_quote = 0
        self.pnl_domestic = 0

    def set_filled_amount(self, filled_amount: float):
        self.filled_amount = filled_amount

    def set_avg_price(self, avg_price: float):
        self.avg_price = avg_price

    def set_commissions(self, commission: float, cntr_commission: float):
        self.commission = commission
        self.cntr_commission = cntr_commission

    def set_realized_pnl_quote(self, pnl_quote: float):
        self.pnl_quote = pnl_quote

    def set_realized_pnl_domestic(self, pnl_domestic: float):
        self.pnl_domestic = pnl_domestic

    def get_request(self) -> 'AccountHedgeRequestInterface':
        return self.request

    def get_filled_amount(self):
        return self.filled_amount

    def get_total_price(self):
        return self.filled_amount * self.avg_price

    def get_pnl_quote(self) -> float:
        return self.pnl_quote

    def get_pnl_domestic(self) -> float:
        return self.pnl_domestic


class AccountHedgeRequestInterface(object):
    """
    Abstract base class for objects that can be used to store account hedge requests.
    """

    @abstractmethod
    def get_fx_pair(self) -> FxPairInterface:
        raise NotImplementedError

    @abstractmethod
    def get_requested_amount(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_account(self) -> AccountInterface:
        raise NotImplementedError

    @abstractmethod
    def create_result_object(self) -> AccountHedgeResultInterface:
        """
        Create an AccountHedgeResultInterface object that can be used to report the result of the request. Having this
        as a member function allow the internal workings of the function to tie the result back to the request, or
        even return the same object, if the object is both a request interface and a result interface (as the
        model AccountHedgeRequest is).
        """
        raise NotImplementedError


class BasicAccountHedgeRequest(AccountHedgeRequestInterface):
    """
    A basic implementation of the AccountHedgeRequestInterface that just stores everything internally.
    """
    def __init__(self, fx_pair: FxPairInterface, amount: float, account: AccountInterface):
        self.fx_pair = fx_pair
        self.amount = amount
        self.account = account

    def get_fx_pair(self) -> FxPairInterface:
        return self.fx_pair

    def get_requested_amount(self) -> float:
        return self.amount

    def get_account(self) -> AccountInterface:
        return self.account

    def create_result_object(self) -> AccountHedgeResultInterface:
        return BasicAccountHedgeResult(self)
