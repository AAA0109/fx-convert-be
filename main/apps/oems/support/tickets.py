from enum import Enum
from typing import Union, Dict

import numpy as np
from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Core.FxPairInterface import FxPairInterface

from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import FxPair, Currency
from main.apps.hedge.models import CompanyHedgeAction


class OMSOrderTicket:
    class States(Enum):
        """ States Enum, taken from OEMS """
        ACCEPTED = 'ACCEPTED'
        BOOKED = 'BOOKED'
        CANCELLED = 'CANCELLED'
        FILLED = 'FILLED'
        NEW = 'NEW'
        OVERFILLED = 'OVERFILLED'
        PARTIAL = 'PARTIAL'
        PAUSED = 'PAUSED'
        PENDAUTH = 'PENDAUTH'
        PENDCANCEL = 'PENDCANCEL'
        PENDFUNDS = 'PENDFUNDS'
        PTLCANCEL = 'PTLCANCEL'
        QUEUED = 'QUEUED'
        REJECTED = 'REJECTED'
        STAGED = 'STAGED'
        WAITING = 'WAITING'
        WORKING = 'WORKING'
        ERROR = 'ERROR'
        FAILED = 'FAILED'

    Unfinished = {
        States.ACCEPTED,
        States.BOOKED,
        States.NEW,
        States.PARTIAL,
        States.PAUSED,
        States.PENDAUTH,
        States.PENDCANCEL,
        States.PENDFUNDS,
        States.QUEUED,
        States.STAGED,
        States.WAITING,
        States.WORKING
    }

    # ==================================
    #  Finished states.
    # ==================================

    FinishedSuccess = {
        States.FILLED,
        States.PTLCANCEL,  # NOTE(Nate): Not sure what this one is, maybe canceled on purpose.
    }

    FinishedWarning = {
        States.OVERFILLED
    }

    FinishedFailure = {
        States.REJECTED,
        States.ERROR,
        States.FAILED
    }

    def __init__(self,
                 fx_pair: FxPairInterface,
                 company_hedge_action: CompanyHedgeAction,
                 amount_filled: float,
                 amount_remaining: float,
                 average_price: float,
                 commission: float,
                 cntr_commission: float,
                 state: States):
        self.fx_pair = fx_pair
        self.company_hedge_action = company_hedge_action

        self.amount_filled = amount_filled
        self.amount_remaining = amount_remaining
        self.average_price = average_price

        self.commission = commission
        self.cntr_commission = cntr_commission

        self.state = state

    @staticmethod
    def make_empty(fx_pair: FxPairHDL, company_hedge_action: CompanyHedgeAction) -> 'OMSOrderTicket':
        return OMSOrderTicket(fx_pair=fx_pair, company_hedge_action=company_hedge_action, amount_filled=0,
                              amount_remaining=0, average_price=0, commission=0, cntr_commission=0,
                              state=OMSOrderTicket.States.FILLED)

    @property
    def total_price(self) -> float:
        return self.amount_filled * self.average_price

    @property
    def cash_position(self) -> Dict[Currency, float]:
        return {
            self.fx_pair.get_base_currency(): self.amount_filled / self.average_price,
            self.fx_pair.get_quote_currency(): -self.amount_filled
        }

    def __str__(self):
        return "{" + f"fxpair: {self.fx_pair}, " \
                     f"company_hedge_action_id: {self.company_hedge_action.id}, " \
                     f"amount_filled: {self.amount_filled}, " \
                     f"average_price: {self.average_price}, " \
                     f"commission: {self.commission}, " \
                     f"cntr_commission: {self.cntr_commission}, " \
                     f"state: {self.state}" \
            + "}"


class OrderTicket:
    """ A ticket that is used to submit an order to the OMS. """

    def __init__(
        self,
        fx_pair: Union[FxPairHDL, FxPair],
        amount: float,
        company_hedge_action: CompanyHedgeAction,
        broker_account: BrokerAccount,
        base_url: str,
        auth_token: str,
    ):
        self.fx_pair = fx_pair if isinstance(fx_pair, FxPairHDL) else fx_pair.to_FxPairHDL()
        self.amount = np.abs(amount)
        self.is_buy = 0 < amount
        self.company_hedge_action = company_hedge_action
        self.broker_account = broker_account
        self.base_url = base_url
        self.auth_token = auth_token

    def make_dict(self) -> dict:
        # TODO: remove hard-coded stuff and allow other options to be passed in.
        ticket = {
            'Market': f"{self.fx_pair.base.get_mnemonic()}{self.fx_pair.quote.get_mnemonic()}",
            'Side': ("Buy" if self.is_buy else "Sell"),
            'TicketType': 'OPEN',
            'Qty': self.amount,
            'HedgeActionId': self.company_hedge_action.id,
            'Company': self.company_hedge_action.company.id,
            "SubDest": "IBKR_FIX",
            "Account": self.broker_account.broker_account_name,
            "DashboardApiUrl": self.base_url,
            "DashboardAuthToken": self.auth_token,
        }
        return ticket

    @property
    def signed_amount(self) -> float:
        return self.amount if self.is_buy else -self.amount
