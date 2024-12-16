import unittest

from django.test import TestCase
from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.broker.models import Broker
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models import AccountDesiredPositions, CompanyHedgeAction


# noinspection DuplicatedCode
class AccountDesiredPositionsTest(TestCase):
    def test_get_most_recent(self):
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        _, broker = Broker.create_broker("TEST_BROKER")

        company1 = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company1.save()

        account1 = Account.create_account(name="DUMMY-1", company=company1)
        account2 = Account.create_account(name="DUMMY-2", company=company1)

        positions1 = {gbpusd: 5000, eurusd: 4000}
        positions2 = {gbpusd: 3500, eurusd: 4400}

        time0 = Date.create(ymd=20200101, hour=16)
        time1 = Date.create(ymd=20200101, hour=21)
        time2 = Date.create(ymd=20200101, hour=23)

        _, hedge_action1 = CompanyHedgeAction.add_company_hedge_action(company=company1, time=time1)
        _, hedge_action2 = CompanyHedgeAction.add_company_hedge_action(company=company1, time=time2)

        # Add desired positions.
        AccountDesiredPositions.add_desired_positions(account=account1, positions=positions1,
                                                      hedge_action=hedge_action1)
        AccountDesiredPositions.add_desired_positions(account=account2, positions=positions2,
                                                      hedge_action=hedge_action1)

        # Check positions

        pos0 = AccountDesiredPositions.get_desired_positions_for_account(account=account1, time=time0)
        self.assertEqual(len(pos0), 0)

        # Check positions at time 1. There should be positions.

        pos1 = AccountDesiredPositions.get_desired_positions_for_account(account=account1, time=time1)
        self.assertEqual(len(pos1), 2)
        self.assertEqual(pos1[gbpusd], 5000)
        self.assertEqual(pos1[eurusd], 4000)

        # Check positions at time 2. Since none were set with the account hedge action at time 2, this means the
        # desired position is zero.

        pos2 = AccountDesiredPositions.get_desired_positions_for_account(account=account1, time=time2)
        self.assertEqual(len(pos2), 0)


if __name__ == '__main__':
    unittest.main()
