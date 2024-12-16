import unittest
from typing import Optional, Dict

import numpy as np
import pandas as pd
from django.test import testcases
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models import CompanyHedgeAction, FxPosition
from main.apps.hedge.services.hedge_position import HedgePositionService


# noinspection DuplicatedCode
class HedgePositionServiceTest(testcases.TestCase):
    def test__has_open_positions(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account = Account.create_account(name="DUMMY", company=company)

        company2 = Company.create_company(name="Nothing", currency=gbp)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)

        self.assertTrue(service.has_open_positions(company=company))
        self.assertFalse(service.has_open_positions(company=company2))

    def test__get_total_value(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        spot_fx_cache_original = DictSpotFxCache(date=time, spots={gbpusd: 1.33, eurusd: 1.22, usdkrw: 102.3})
        spot_fx_cache = DictSpotFxCache(date=time, spots={gbpusd: 1.35, eurusd: 1.40, usdkrw: 105.5})

        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache_original, company=company)
        # self.assertAlmostEqual(value, 0, delta=1.e-4)
        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache, company=company)
        self.assertAlmostEqual(value, 155.4976, delta=1.e-4)
        self.assertEqual(currency, usd)

        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache_original, account=account1)
        self.assertAlmostEqual(value, 0, delta=1.e-4)
        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache, account=account1)
        self.assertAlmostEqual(value, 116.2654, delta=1.e-4)
        self.assertEqual(currency, usd)

        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache_original, account=account2)
        self.assertAlmostEqual(value, 0, delta=1.e-4)
        value, currency = service.get_total_value(spot_fx_cache=spot_fx_cache, account=account2)
        self.assertAlmostEqual(value, 39.2322, delta=1.e-4)
        self.assertEqual(currency, usd)

    def test__get_position_objects(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        positions = service.get_position_objects(company=company, date=time - 1)
        self.assertEqual(len(positions), 0)

        positions = service.get_position_objects(company=company, date=time)
        self.assertEqual(len(positions), 5)
        positions = service.get_position_objects(account=account1, date=time)
        self.assertEqual(len(positions), 3)
        positions = service.get_position_objects(account=account2, date=time)
        self.assertEqual(len(positions), 2)

    def test__get_virtual_fx_positions(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        virtual_fx_positions = service.get_virtual_fx_positions(company=company, date=time)
        self.assertEqual(len(virtual_fx_positions), 3)
        self.assertEqual(virtual_fx_positions[0].fxpair, gbpusd)
        self.assertEqual(virtual_fx_positions[0].base_cash, 100)
        self.assertEqual(virtual_fx_positions[0].quote_cash, -133)
        self.assertEqual(virtual_fx_positions[1].fxpair, eurusd)
        self.assertEqual(virtual_fx_positions[1].base_cash, 500)
        self.assertEqual(virtual_fx_positions[1].quote_cash, -610)
        self.assertEqual(virtual_fx_positions[2].fxpair, usdkrw)
        self.assertEqual(virtual_fx_positions[2].base_cash, 800)
        self.assertEqual(virtual_fx_positions[2].quote_cash, -81840)

    def test__get_cash_positions(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        cash_positions, objs = service.get_cash_positions(company=company)
        self.assertEqual(cash_positions.cash_by_currency[gbp], 100)
        self.assertEqual(cash_positions.cash_by_currency[usd], 635)
        self.assertEqual(cash_positions.cash_by_currency[eur], 600)
        self.assertEqual(cash_positions.cash_by_currency[krw], -153_450)

        cash_positions, objs = service.get_cash_positions(account=account1)
        self.assertEqual(cash_positions.cash_by_currency[gbp], 100)
        self.assertEqual(cash_positions.cash_by_currency[usd], 57)
        self.assertEqual(cash_positions.cash_by_currency[eur], 500)
        self.assertEqual(cash_positions.cash_by_currency[krw], -81_840)

        cash_positions, objs = service.get_cash_positions(account=account2)
        self.assertEqual(cash_positions.cash_by_currency.get(gbp, 0), 0)
        self.assertEqual(cash_positions.cash_by_currency.get(usd, 0), 578)
        self.assertEqual(cash_positions.cash_by_currency.get(eur, 0), 100)
        self.assertEqual(cash_positions.cash_by_currency.get(krw, 0), -71_610)

    def test__get_all_positions_for_accounts_for_company_by_pair(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        positions = service.get_all_positions_for_accounts_for_company_by_pair(company=company, time=time)
        self.assertEqual(len(positions), 3)
        self.assertTrue(eurusd in positions)
        self.assertTrue(gbpusd in positions)
        self.assertTrue(usdkrw in positions)
        self.assertEqual(len(positions[eurusd]), 2)
        self.assertEqual(len(positions[gbpusd]), 1)
        self.assertEqual(len(positions[usdkrw]), 2)

    def test__get_positions_for_account_for_fxpairs(self):
        service = HedgePositionService()
        # service.get_positions_for_account_for_fxpairs

    def test__get_positions_for_company_by_account(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        positions = service.get_positions_for_company_by_account(company=company)
        self.assertEqual(len(positions), 2)
        self.assertEqual(len(positions[account1]), 3)
        self.assertEqual(len(positions[account2]), 2)

    def test__get_aggregate_positions_for_company(self):
        service = HedgePositionService()

        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, gbp = Currency.create_currency('GBP', 'GBP', 'GBP')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')
        _, krw = Currency.create_currency('KRW', 'KRW', 'KRW')

        _, gbpusd = FxPair.create_fxpair(base=gbp, quote=usd)
        _, eurusd = FxPair.create_fxpair(base=eur, quote=usd)
        _, usdkrw = FxPair.create_fxpair(base=usd, quote=krw)

        company = Company.create_company(name="ACME", currency=usd)
        account1 = Account.create_account(name="DUMMY", company=company)
        account2 = Account.create_account(name="BUMMY", company=company)

        time = Date.create(year=2020, month=2, day=15, hour=12, minute=16, second=33)
        _, first_action = CompanyHedgeAction.add_company_hedge_action(company=company, time=time)

        service.set_single_position_for_account(account=account1, amount=100, fx_pair=gbpusd,
                                                company_hedge_action=first_action, spot_rate=1.33)
        service.set_single_position_for_account(account=account1, amount=500, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account1, amount=800, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        service.set_single_position_for_account(account=account2, amount=100, fx_pair=eurusd,
                                                company_hedge_action=first_action, spot_rate=1.22)
        service.set_single_position_for_account(account=account2, amount=700, fx_pair=usdkrw,
                                                company_hedge_action=first_action, spot_rate=102.3)

        positions = service.get_aggregate_positions_for_company(company=company)
        self.assertEqual(len(positions), 3)
        self.assertEqual(positions[gbpusd], 100)
        self.assertEqual(positions[eurusd], 600)
        self.assertEqual(positions[usdkrw], 1500)


if __name__ == '__main__':
    unittest.main()
