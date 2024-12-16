import numpy as np
from typing import Optional

from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.FxPairInterface import FxPairInterface


# TODO: Move to HDLib
class FxPositionInterface:
    def get_fxpair(self) -> FxPairInterface:
        raise NotImplementedError

    def get_amount(self) -> float:
        raise NotImplementedError

    def get_total_price(self) -> float:
        raise NotImplementedError

    def get_account(self) -> AccountInterface:
        raise NotImplementedError

    def get_average_price(self) -> float:
        return self.get_total_price() / np.abs(self.get_amount()) if self.get_amount() != 0 else 0.

    def get_signed_total_price(self) -> float:
        return np.sign(self.get_amount()) * self.get_total_price()


# TODO: Move to HDLib
class BasicFxPosition(FxPositionInterface):
    def __init__(self,
                 fxpair: FxPairInterface,
                 amount: float,
                 total_price: float,
                 account: Optional[AccountInterface] = None):
        self.fxpair = fxpair
        self.amount = amount
        self.total_price = total_price
        self.account = account

    def get_fxpair(self) -> FxPairInterface:
        return self.fxpair

    def get_amount(self) -> float:
        return self.amount

    def get_total_price(self) -> float:
        return self.total_price

    def get_account(self) -> AccountInterface:
        return self.account
