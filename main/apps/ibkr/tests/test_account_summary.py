from hdlib.DateTime.Date import Date

from main.apps.account.models import Account
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.account.models.test.base import BaseTestCase
from main.apps.ibkr.models import IbkrAccountSummary


class TestAccountSummary(BaseTestCase):
    def test_account_summary_no_broker(self):
        summary = IbkrAccountSummary.get_broker_account_summary(company=self.company1,
                                                                account_type=Account.AccountType.LIVE,
                                                                date=Date.today())
        self.assertEqual(summary, None)

    def test_account_summary_no_summary(self):
        _, broker = Broker.create_broker(name="Test Broker")
        _, broke_account_live = BrokerAccount.create_account_for_company(company=self.company1,
                                                                         broker=broker,
                                                                         broker_account_name="Live broker account",
                                                                         account_type=BrokerAccount.AccountType.LIVE)
        _, broke_account_demo = BrokerAccount.create_account_for_company(company=self.company1,
                                                                         broker=broker,
                                                                         broker_account_name="Demo broker account",
                                                                         account_type=BrokerAccount.AccountType.PAPER)

        summary = IbkrAccountSummary.get_broker_account_summary(company=self.company1,
                                                                account_type=BrokerAccount.AccountType.LIVE,
                                                                date = Date.today())
        self.assertEqual(summary, None)

    def test_account_summary(self):
        _, broker = Broker.create_broker(name="Test Broker")
        _, broke_account_live = BrokerAccount.create_account_for_company(company=self.company1,
                                                                         broker=broker,
                                                                         broker_account_name="Live broker account",
                                                                         account_type=BrokerAccount.AccountType.LIVE)
        _, broke_account_demo = BrokerAccount.create_account_for_company(company=self.company1,
                                                                         broker=broker,
                                                                         broker_account_name="Demo broker account",
                                                                         account_type=BrokerAccount.AccountType.PAPER)

        summary = IbkrAccountSummary.objects.create(
            broker_account=broke_account_live,
            account_type="Margin",
            cushion=1,
            look_ahead_next_change=2,
            accrued_cash=3,
            available_funds=4,
            buying_power=5,
            equity_with_loan_value=7,
            excess_liquidity=8,
            full_init_margin_req=9,
            full_maint_margin_req=10,
            full_available_funds=11,
            full_excess_liquidity=12,
            gross_position_value=13,
            init_margin_req=14,
            maint_margin_req=15,
            look_ahead_available_funds=16,
            look_ahead_excess_liquidity=17,
            look_ahead_init_margin_req=18,
            look_ahead_maint_margin_req=19,
            net_liquidation=21,
            sma=22,
            total_cash_value=23,
        )
        summary = IbkrAccountSummary.get_broker_account_summary(company=self.company1,
                                                                account_type=Account.AccountType.DEMO,
                                                                date = Date.now())

        self.assertEqual(summary, None)

        summary = IbkrAccountSummary.get_broker_account_summary(company=self.company1,
                                                                account_type=Account.AccountType.LIVE,
                                                                date=Date.now())
        self.assertEqual(summary.sma, 22)

