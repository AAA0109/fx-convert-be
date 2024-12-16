import unittest
from typing import Dict

from django.test import TestCase
from hdlib.Core.AccountInterface import AccountInterface
from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache, DictSpotFxCache

from hdlib.DateTime.Date import Date

# noinspection DuplicatedCode
from main.apps.account.models import Company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.models import CompanyFxPosition, CompanyEvent, AccountHedgeRequest
from main.apps.hedge.services.broker_reconcile import BrokerReconcileService, ReconciliationCallback
from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface
from main.apps.hedge.support.fxposition_interface import FxPositionInterface


class TestReconciliationCallback(ReconciliationCallback):

    def update_hedge_result(self, result: AccountHedgeResultInterface,
                            status: AccountHedgeRequest.OrderStatus = AccountHedgeRequest.OrderStatus.CLOSED):
        pass

    def create_company_positions(self, company: Company, time: Date, spot_cache: SpotFxCache) -> CompanyEvent:
        event = CompanyEvent.get_or_create_event(company=company, time=time)
        return event

    def create_reconciliation_records(self, company: Company, time: Date, reconciliation_data, is_live: bool):
        pass

    def create_fx_positions(self, final_positions_by_fxpair: Dict[
        FxPairInterface, Dict[AccountInterface, FxPositionInterface]], company_event: CompanyEvent):
        pass


class BrokerReconcileServiceTest(TestCase):

    def test_unrealized_pnl(self):
        reconcile = BrokerReconcileService()
        ref_date = Date.create(ymd=20210101, hour=20)

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

        spot_cache = DictSpotFxCache(date=ref_date, spots={gbpusd: 1.2, eurusd: 1.18, usdkrw: 102.3})

        callback = TestReconciliationCallback()

        # Expect that this does not throw.
        reconcile.reconcile_company(time=ref_date, company=company1, spot_cache=spot_cache, callback=callback)


if __name__ == '__main__':
    unittest.main()
