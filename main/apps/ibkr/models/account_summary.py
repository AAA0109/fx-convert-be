import logging
from typing import Optional

from auditlog.registry import auditlog
from django.db import models
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime import Date

from main.apps.account.models import Company, Account
from main.apps.broker.models import BrokerAccount
from main.apps.util import get_or_none

logger = logging.getLogger(__name__)


class IbkrAccountSummary(TimeStampedModel):
    # The broker account this summary is for
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name='account_summaries')

    # Identifies the IB account structure. Note that this is different from the account type used internally.
    account_type = models.CharField(max_length=255, null=True)

    # Excess liquidity as a percentage of net liquidation value
    cushion = models.FloatField()

    # Shows you when the next margin period will begin.
    look_ahead_next_change = models.FloatField()

    # total accrued cash value of stock, commodities and securities
    accrued_cash = models.FloatField()

    # Available funds: This value tells what you have available for trading.
    #             Securities: Equal to (Equity with Loan Value) - (Initial margin).
    #             Commodities: Equal to (Net Liquidation Value) - (Initial Margin).
    available_funds = models.FloatField()

    # Buying power serves as a measurement of the dollar value of securities that
    # one may purchase in a securities account without depositing additional funds
    buying_power = models.FloatField()

    #  Forms the basis for determining whether a client has the necessary assets to either initiate or maintain
    #  security positions.
    #               Cash + stocks + bonds + mutual funds
    equity_with_loan_value = models.FloatField()

    # Excess liquidity: This value shows your margin cushion, before liquidation.
    #             Securities: Equal to (Equity with Loan Value) - (Maintenance margin).
    #             Commodities: Equal to (Net Liquidation value) - (Maintenance margin).
    excess_liquidity = models.FloatField()

    # Available funds of whole portfolio with no discounts or intraday credits
    full_available_funds = models.FloatField()

    # Excess liquidity of whole portfolio with no discounts or intraday credits
    full_excess_liquidity = models.FloatField()

    # Initial Margin of whole portfolio with no discounts or intraday credits
    full_init_margin_req = models.FloatField()

    # Maintenance Margin of whole portfolio with no discounts or intraday credits
    full_maint_margin_req = models.FloatField()

    # Gross Position Value: Equals the sum of the absolute value of all positions except cash, index futures and
    #             US treasuries.
    gross_position_value = models.FloatField()

    # Initial Margin requirement of whole portfolio
    init_margin_req = models.FloatField()

    # Maintenance Margin requirement of whole portfolio
    maint_margin_req = models.FloatField()

    # Look ahead available funds: This value reflects your available funds at the next margin change. The next
    #             change is displayed in the Look Ahead Next Change field.
    #             Equal to (Equity with loan value) - (look ahead initial margin).
    look_ahead_available_funds = models.FloatField()

    # Equity with loan value - look ahead maintenance margin.
    look_ahead_excess_liquidity = models.FloatField()

    # Intial Margin requirement of whole portfolio as of next period's margin change
    look_ahead_init_margin_req = models.FloatField()

    # Maint Margin requirement of whole portfolio as of next period's margin change
    look_ahead_maint_margin_req = models.FloatField()

    # The basis for determining the price of the assets in an account.
    #       Total cash value + stock value + options value + bond value
    net_liquidation = models.FloatField()
    #  Special Memorandum Account - see https://ibkr.info/node/66
    sma = models.FloatField()

    # Total cash balance recognized at the time of trade + futures PNL
    total_cash_value = models.FloatField()

    @staticmethod
    @get_or_none
    def get_broker_account_summary(company: Company,
                                   account_type: Account.AccountType,
                                   date: Date) -> Optional['IbkrAccountSummary']:
        if account_type == Account.AccountType.DEMO:
            account_types = (BrokerAccount.AccountType.PAPER,)
        else:
            account_types = (BrokerAccount.AccountType.LIVE,)

        broker_accounts = BrokerAccount.get_accounts_for_company(company=company, account_types=account_types)
        if not broker_accounts:
            return None
        broker_account = broker_accounts[0]
        filters = {"broker_account": broker_account, "created__lte": date}
        return IbkrAccountSummary.objects.filter(**filters).order_by('-created').first()


auditlog.register(IbkrAccountSummary)
