import unittest

from django.test import TestCase
from hdlib.Core.Currency import USD

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.broker.models import Broker
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models import CompanyEvent, FxPosition


# noinspection DuplicatedCode
class AccountFxPositionsTest(TestCase):
    def test_basic_functionality(self):
        """ Test that FxPosition correctly functions as an FxPositionInterface """
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)

        company = Company.objects.create(name='Test Company', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company.save()
        account = Account.create_account(name="DUMMY", company=company)

        positions = {gbpusd: (5000, 5000 * 1.1)}
        time = Date.create(ymd=20200101, hour=21)
        event = CompanyEvent.get_or_create_event(company=company, time=time)

        fx_positions = FxPosition.raw_create_positions(account=account, company_event=event, positions=positions)

        count = 0
        for fx_position in fx_positions:
            # FxPositionInterfact tests.
            self.assertEqual(fx_position.get_fxpair(), gbpusd)
            self.assertEqual(fx_position.get_amount(), 5000)
            self.assertEqual(fx_position.get_total_price(), 5000 * 1.1)
            self.assertEqual(fx_position.get_account(), account)

            # Other tests
            self.assertEqual(fx_position.average_price, (1.1, USD))
            self.assertFalse(fx_position.is_empty)
            self.assertTrue(fx_position.is_long)
            self.assertEqual(fx_position.unrealized_pnl(current_rate=1.22), (5000 * 0.12, USD))

            count += 1
        self.assertEqual(count, 1)  # There should have been only one object

    def test_get_most_recent(self):
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.objects.create(name='Test Company', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company.save()
        account = Account.create_account(name="DUMMY", company=company)

        positions1 = {gbpusd: (5000, 5000 * 1.1), eurusd: (4000, 4000 * 1.15)}
        # No positions will be at time 2.
        positions3 = {gbpusd: (3500, 5000 * 1.2), eurusd: (4400, 4400 * 1.13)}

        time1 = Date.create(ymd=20200101, hour=21)
        time2 = Date.create(ymd=20200101, hour=23)
        time3 = Date.create(ymd=20200102, hour=21)

        event1 = CompanyEvent.get_or_create_event(company=company, time=time1)
        event2 = CompanyEvent.get_or_create_event(company=company, time=time2)
        event3 = CompanyEvent.get_or_create_event(company=company, time=time3)

        # Add positions for event1.
        FxPosition.raw_create_positions(account=account, company_event=event1, positions=positions1)
        # Set zero positions at event2.
        FxPosition.raw_create_positions(account=account, company_event=event2, positions={})
        # Add positions for event 3
        FxPosition.raw_create_positions(account=account, company_event=event3, positions=positions3)

        # Check positions
        self.assertTrue(event1.has_account_fx_snapshot)
        self.assertTrue(event2.has_account_fx_snapshot)
        self.assertTrue(event3.has_account_fx_snapshot)

        positions_at_1, event = FxPosition.get_position_objs(account=account, time=time1)
        self.assertEqual(len(positions_at_1), 2)
        self.assertEqual(event, event1)
        positions_at_2, event = FxPosition.get_position_objs(account=account, time=time2)
        self.assertEqual(len(positions_at_2), 0)
        self.assertEqual(event, event2)
        positions_at_3, event = FxPosition.get_position_objs(account=account, time=time3)
        self.assertEqual(len(positions_at_3), 2)
        self.assertEqual(event, event3)


if __name__ == '__main__':
    unittest.main()
