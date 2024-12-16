import unittest

from django.test import TestCase
from hdlib.DateTime.Date import Date
from main.apps.account.models import Company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models.company_fxposition import CompanyFxPosition

_DEMO = BrokerAccount.AccountType.PAPER


# noinspection DuplicatedCode
class CompanyFxPositionsTest(TestCase):
    def test_unrealized_pnl(self):
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

        _, live_broker_account = BrokerAccount.create_account_for_company(company=company1,
                                                                          account_type=BrokerAccount.AccountType.LIVE,
                                                                          broker=broker,
                                                                          broker_account_name="U1")

        positions, _ = CompanyFxPosition.create_company_positions(time=Date.now(),
                                                                  broker_account=live_broker_account,
                                                                  company=company1,
                                                                  positions={gbpusd: (1000, 1000 * 1.2),
                                                                             eurusd: (500, 500 * 1.18),
                                                                             usdkrw: (1400, 1400 * 102.3)})
        current_rates = {gbpusd: 1.32, eurusd: 1.21, usdkrw: 105.25}
        expected_unrealized_pnl = {gbpusd: 1000 * (1.32 - 1.20),
                                   eurusd: 500 * (1.21 - 1.18),
                                   usdkrw: 1400 * (105.25 - 102.3)}
        for pos in positions:
            self.assertAlmostEqual(pos.unrealized_pnl(current_rate=current_rates[pos.fxpair])[0],
                                   expected_unrealized_pnl[pos.fxpair], delta=0.0001)

    def test_queries(self):
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        _, broker = Broker.create_broker("TEST_BROKER")

        # ================================================
        #  Create first company.
        # ================================================

        company1 = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company1.save()

        _, live_broker_account = BrokerAccount.create_account_for_company(company=company1,
                                                                          account_type=BrokerAccount.AccountType.LIVE,
                                                                          broker=broker,
                                                                          broker_account_name="U1")
        _, paper_broker_account = BrokerAccount.create_account_for_company(company=company1,
                                                                           account_type=BrokerAccount.AccountType.PAPER,
                                                                           broker=broker,
                                                                           broker_account_name="U2")

        # ================================================
        #  Create second company.
        # ================================================

        company2 = Company.objects.create(name='Test Company 2', currency=gbp, status=Company.CompanyStatus.ACTIVE)
        company2.save()

        # ================================================
        #  Add some positions.
        # ================================================

        time = Date.create(year=2020, month=1, day=1, hour=23, minute=30)
        positions = {eurusd: (1000, 1.2 * 1000), gbpusd: (1500, 1.12 * 1500)}
        company_positions, _ = CompanyFxPosition.create_company_positions(time=time,
                                                                          broker_account=live_broker_account,
                                                                          company=company1,
                                                                          positions=positions)
        self.assertEqual(len(company_positions), 2)

        time = Date.create(year=2020, month=1, day=1, hour=23, minute=46)
        positions = {eurusd: (1010, 1.2 * 1010), gbpusd: (1254, 1.13 * 1254)}
        company_positions, _ = CompanyFxPosition.create_company_positions(time=time,
                                                                          broker_account=live_broker_account,
                                                                          company=company1,
                                                                          positions=positions)
        self.assertEqual(len(company_positions), 2)

        ime = Date.create(year=2020, month=1, day=1, hour=23, minute=46)
        positions = {eurusd: (500, 1.2 * 500), gbpusd: (500, 1.13 * 500), usdkrw: (12000, 102.50 * 12000)}
        company_positions, _ = CompanyFxPosition.create_company_positions(time=time,
                                                                          broker_account=paper_broker_account,
                                                                          company=company1,
                                                                          positions=positions)
        self.assertEqual(len(company_positions), 3)

        # This should get the most recent positions.
        _, objs = CompanyFxPosition.get_position_objs_for_company(company=company1)
        self.assertEqual(len(objs), 5)
        for obj in objs:
            self.assertEqual(obj.snapshot_event.time, Date.create(year=2020, month=1, day=1, hour=23, minute=46))

        # This should get just the most recent live positions.
        _, objs = CompanyFxPosition.get_position_objs_for_company(company=company1,
                                                                  positions_type=BrokerAccount.AccountType.LIVE)
        self.assertEqual(len(objs), 2)
        # This should get the most recent paper positions.
        _, objs = CompanyFxPosition.get_position_objs_for_company(company=company1,
                                                                  positions_type=BrokerAccount.AccountType.PAPER)
        self.assertEqual(len(objs), 3)

        # Get positions as of an earlier time, should get the first positions for the company.
        time = Date.create(year=2020, month=1, day=1, hour=23, minute=32)
        _, objs = CompanyFxPosition.get_position_objs_for_company(company=company1, time=time)
        self.assertEqual(len(objs), 2)
        for obj in objs:
            self.assertEqual(obj.snapshot_event.time, Date.create(year=2020, month=1, day=1, hour=23, minute=30))

        _, positions_by_broker_account = CompanyFxPosition.get_account_positions_by_broker_account(company=company1)
        self.assertEqual(len(positions_by_broker_account), 2)
        self.assertTrue(live_broker_account in positions_by_broker_account)
        self.assertTrue(paper_broker_account in positions_by_broker_account)
        self.assertEqual(len(positions_by_broker_account[live_broker_account]), 2)
        self.assertEqual(len(positions_by_broker_account[paper_broker_account]), 3)


if __name__ == '__main__':
    unittest.main()
