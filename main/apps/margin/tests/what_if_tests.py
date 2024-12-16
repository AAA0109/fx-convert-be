import unittest.mock as mock

import pandas as pd
from django.db.models.signals import post_save
from django.test import TestCase
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import Company, Account, CashFlow
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models import Currency
from main.apps.hedge.models import HedgeSettings
from main.apps.margin.models import MarginDetail
from main.apps.margin.services.broker_margin_service import BrokerMarginRequirements
from main.apps.margin.services.calculators import MarginRatesCache
from main.apps.margin.services.what_if import WhatIfMarginService


# noinspection DuplicatedCode
class WhatIfTests(TestCase):

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.hedge.services.hedger.CompanyHedgerFactory")
    @mock.patch("main.apps.margin.services.margin_service.DefaultMarginProviderService")
    def test_no_cashflow_no_broker_account(self,
                                           margin_calculator,
                                           broker_margin_service,
                                           margin_rates_cache_provider,
                                           cash_flow_provider,
                                           fx_spot_provider,
                                           hedge_position_service,
                                           margin_detail_service,
                                           pnl_calculator,
                                           hedger_factory,
                                           margin_provider_service):
        """
        :param margin_calculator:
        :param broker_margin_service:
        :param margin_rates_cache_provider:
        :param cash_flow_provider:
        :param fx_spot_provider:
        :param hedge_position_service:
        :param margin_detail_service:
        :param pnl_calculator:
        :return:
        """
        date = Date.today()
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')

        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        account = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        account.is_active = True
        account.save()
        _ = HedgeSettings.create_or_update_settings(account=account, margin_budget=100000, custom={})
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)
        spot_fx_cache = DictSpotFxCache(date=date, spots={"EUR/USD": 1.05, "USD/EUR": 1 / 1.05})
        fx_spot_provider.get_eod_spot_fx_cache = mock.MagicMock(return_value=spot_fx_cache)
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        broker_margin_requirement = BrokerMarginRequirements(init_margin=0, maint_margin=0, excess_liquidity=0,
                                                             additional_cash=0, equity_with_loan_value=0)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(return_value=broker_margin_requirement)
        pnl_calculator.calc_realized_pnl_of_position_change = mock.MagicMock(return_value=0)
        margin_calculator.compute_margin_from_vfx = mock.MagicMock(return_value=0)
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(CashPositions(), []))
        cashflows = []

        service = WhatIfMarginService(margin_calculator=margin_calculator,
                                      broker_service=broker_margin_service,
                                      margin_rates_cache_provider=margin_rates_cache_provider,
                                      fx_spot_provider=fx_spot_provider,
                                      hedge_position_service=hedge_position_service,
                                      pnl_calculator=pnl_calculator,
                                      hedger_factory=hedger_factory,
                                      margin_provider_service=margin_provider_service)
        hedger = mock.MagicMock()
        position_changes = PositionChange(old_positions=pd.Series(dtype=float),
                                          new_positions=pd.Series(dtype=float), settings=None)
        hedger.hedge_company = mock.MagicMock(return_value=((None, position_changes, None), None))
        hedger_factory.create = mock.MagicMock(return_value=hedger)

        response_margin_detail = MarginDetail(company=company, date=date, margin_requirement=0, excess_liquidity=0)
        margin_provider_service.compute_margin_for_position = mock.MagicMock(return_value=response_margin_detail)
        margin_details = service.get_margin_details_what_if_after_trades(date=date,
                                                                         company=company,
                                                                         new_cashflows=cashflows,
                                                                         account_type=Account.AccountType.LIVE)

        self.assertEqual(0, margin_details.margin_requirement)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.hedge.services.hedger.CompanyHedgerFactory")
    @mock.patch("main.apps.margin.services.margin_service.DefaultMarginProviderService")
    def test_no_cashflow_single_cashflow(self,
                                         margin_calculator,
                                         broker_margin_service,
                                         margin_rates_cache_provider,
                                         cash_flow_provider,
                                         fx_spot_provider,
                                         hedge_position_service,
                                         margin_detail_service,
                                         pnl_calculator,
                                         hedger_factory,
                                         margin_provider_service):
        """
        :param margin_calculator:
        :param broker_margin_service:
        :param margin_rates_cache_provider:
        :param cash_flow_provider:
        :param fx_spot_provider:
        :param hedge_position_service:
        :param margin_detail_service:
        :param pnl_calculator:
        :return:
        """

        date = Date.today()
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, eur = Currency.create_currency('EUR', 'EUR', 'EUR')

        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=usd, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        account = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        account.is_active = True
        account.save()
        _ = HedgeSettings.create_or_update_settings(account=account, margin_budget=100000, custom={})
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)
        spot_fx_cache = DictSpotFxCache(date=date, spots={"EUR/USD": 1.05, "USD/EUR": 1 / 1.05})
        fx_spot_provider.get_eod_spot_fx_cache = mock.MagicMock(return_value=spot_fx_cache)
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        broker_margin_requirement = BrokerMarginRequirements(init_margin=0, maint_margin=0, excess_liquidity=0,
                                                             additional_cash=0, equity_with_loan_value=0)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(return_value=broker_margin_requirement)
        pnl_calculator.calc_realized_pnl_of_position_change = mock.MagicMock(return_value=0)
        margin_calculator.compute_margin_from_vfx = mock.MagicMock(return_value=100)
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(CashPositions(), []))

        cf = CashFlow.create_cashflow(account=account,
                                      date=date,
                                      currency=eur,
                                      amount=1000,
                                      status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        cashflows = [cf]

        service = WhatIfMarginService(margin_calculator=margin_calculator,
                                      broker_service=broker_margin_service,
                                      margin_rates_cache_provider=margin_rates_cache_provider,
                                      fx_spot_provider=fx_spot_provider,
                                      hedge_position_service=hedge_position_service,
                                      pnl_calculator=pnl_calculator,
                                      hedger_factory=hedger_factory,
                                      margin_provider_service=margin_provider_service)
        hedger = mock.MagicMock()
        position_changes = PositionChange(old_positions=pd.Series(index=[], data=[], dtype=float),
                                          new_positions=pd.Series(index=["EUR/USD"], data=[1000.0], dtype=float),
                                          settings=None)

        hedger.get_hedge = mock.MagicMock(return_value=(position_changes, None))
        hedger.hedge_company = mock.MagicMock(return_value=((None, position_changes, None), None))
        hedger_factory.create = mock.MagicMock(return_value=hedger)
        response_margin_detail = MarginDetail(company=company, date=date, margin_requirement=100.0, excess_liquidity=0)
        margin_provider_service.compute_margin_for_position = mock.MagicMock(return_value=response_margin_detail)
        margin_details = service.get_margin_details_what_if_after_trades(date=date,
                                                                         company=company,
                                                                         new_cashflows=cashflows,
                                                                         account_type=Account.AccountType.LIVE)

        self.assertEqual(100, margin_details.margin_requirement)
