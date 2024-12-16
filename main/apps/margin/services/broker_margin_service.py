import abc
from enum import Enum
from typing import Optional

from hdlib.DateTime.Date import Date

from main.apps.account.models import Account, Company
from main.apps.broker.models import BrokerAccount
from main.apps.ibkr.models import IbkrAccountSummary


class MarginHealthStatus(Enum):
    Excess = 1
    Healthy = 2
    DepositRequired = 3
    Liquidation = 4


class MarginHealth(object):
    def __init__(self, excess_liquidity: float, init_margin: float, maint_margin: float):
        # Check requirements.
        if init_margin < 0:
            raise ValueError(f"initial margin cannot be less than zero")
        if maint_margin < 0:
            raise ValueError("maintenance margin cannot be less than zero")

        max_ = max(init_margin, maint_margin)
        self.ratio = excess_liquidity / (2 * max_) if 0 < max_ else 1.0

    @property
    def is_healthy(self):
        return self.status == MarginHealthStatus.Healthy or self.status == MarginHealthStatus.Excess

    @property
    def is_unhealthy(self):
        return self.status not in (MarginHealthStatus.Healthy, MarginHealthStatus.Excess)

    @property
    def status(self):
        if self.ratio >= 1:
            return MarginHealthStatus.Excess
        if self.ratio >= 0.5:
            return MarginHealthStatus.Healthy
        if self.ratio >= 0.2:
            return MarginHealthStatus.DepositRequired
        return MarginHealthStatus.Liquidation

    @classmethod
    def from_margin_requirements(cls, summary):
        return cls(summary.excess_liquidity, summary.init_margin, summary.maint_margin)

    @staticmethod
    def make_healthy():
        return MarginHealth(excess_liquidity=0.0, init_margin=0.0, maint_margin=0.0)


class BrokerMarginRequirements(object):
    def __init__(self, init_margin: float, maint_margin: float, excess_liquidity: float, additional_cash: float,
                 equity_with_loan_value: float):
        self.init_margin = init_margin
        self.maint_margin = maint_margin
        self.excess_liquidity = excess_liquidity
        self.additional_cash = additional_cash
        self.equity_with_loan_value = equity_with_loan_value


class BrokerMarginServiceInterface(abc.ABC):
    @abc.abstractmethod
    def get_broker_margin_summary(self,
                                  company: Company,
                                  account_type: Account.AccountType) -> BrokerMarginRequirements:
        """
        Get the broker account summary for the given company and account type.
        """
        raise NotImplementedError()

    def get_broker_for_company(self,
                               company: Company,
                               account_type: Account.AccountType) -> Optional[BrokerAccount]:
        """
        Get the broker for the given company and account type.
        """
        if account_type == Account.AccountType.DEMO:
            account_types = (BrokerAccount.AccountType.PAPER,)
        else:
            account_types = (BrokerAccount.AccountType.LIVE,)

        broker_accounts = BrokerAccount.get_accounts_for_company(company=company, account_types=account_types)
        if broker_accounts:
            return broker_accounts[0]
        return None

    def get_margin_health(self, company: Company) -> MarginHealth:
        """
        Get the margin health for the given company and account type.
        """
        if not company.has_live_accounts():
            # Return a health margin health indicator with zero maintenance/initial margins.
            return MarginHealth.make_healthy()

        summary = self.get_broker_margin_summary(company, Account.AccountType.LIVE)
        return MarginHealth.from_margin_requirements(summary)


class DbBrokerMarginService(BrokerMarginServiceInterface):
    def get_broker_margin_summary(self, company: Company,
                                  account_type: Account.AccountType) -> BrokerMarginRequirements:
        date = Date.now()
        summary = IbkrAccountSummary.get_broker_account_summary(company=company, account_type=account_type, date=date)

        if not summary:
            raise Exception(f'None broker account summary for company {company.name}')

        maint_margin = summary.full_maint_margin_req
        init_margin = summary.full_init_margin_req
        excess_liquidity = summary.full_excess_liquidity
        additional_cash = summary.available_funds
        return BrokerMarginRequirements(init_margin=init_margin,
                                        maint_margin=maint_margin,
                                        excess_liquidity=excess_liquidity,
                                        additional_cash=additional_cash,
                                        equity_with_loan_value=summary.equity_with_loan_value)

