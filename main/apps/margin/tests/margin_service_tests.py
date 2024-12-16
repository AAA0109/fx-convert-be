import unittest.mock as mock
from typing import List, Tuple

from django.db.models.signals import post_save
from django.test import TestCase
from hdlib.Core.Currency import USD, EUR
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import Company, Account
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models import Currency
from main.apps.hedge.models import HedgeSettings
from main.apps.margin.services.broker_margin_service import BrokerMarginRequirements
from main.apps.margin.services.calculators import MarginRatesCache
from main.apps.margin.services.margin_service import MarginProviderService


class MyCashPositions(CashPositions):
    def __eq__(self, other):
        return self.cash_by_currency == other.cash_by_currency

    def __ne__(self, other):
        return not self.__eq__(other)


# noinspection DuplicatedCode
class GetMarginDetailTests(TestCase):


    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_cashflow_no_broker_account(self,
                                           margin_calculator,
                                           broker_margin_service,
                                           margin_rates_cache_provider,
                                           cash_flow_provider,
                                           fx_spot_provider,
                                           hedge_position_service,
                                           margin_detail_service,
                                           pnl_calculator,
                                           deposit_service):
        """
        Test that if there is no cashflow and no broker account, then the margin is 0
        """
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        _ = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        BrokerAccount.create_account_for_company(company=company,
                                                 broker=broker,
                                                 broker_account_name="broker_acocunt",
                                                 account_type=BrokerAccount.AccountType.LIVE)

        # I expect only two method calls.
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(CashPositions(), []))
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(
            return_value=BrokerMarginRequirements(0, 0, 0, 0, 0))

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)

        self.assertEqual(0, service.get_margin_detail(company, date).margin_requirement)
        detail = service.get_margin_detail(company=company, date=date)
        hedge_position_service.get_cash_positions.assert_called_with(company=company, date=date)
        self.assertEqual(0, detail.margin_requirement)
        self.assertEqual(0, detail.excess_liquidity)
        self.assertEqual(company, detail.company)
        self.assertEqual(date, detail.date)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_positions_but_broker_cash(self,
                                          margin_calculator,
                                          broker_margin_service,
                                          margin_rates_cache_provider,
                                          cash_flow_provider,
                                          fx_spot_provider,
                                          hedge_position_service,
                                          margin_detail_service,
                                          pnl_calculator,
                                          deposit_service):
        """
        Test that if we have excess cash at the broker account then it is refelcted here.
        """
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        _ = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        BrokerAccount.create_account_for_company(company=company,
                                                 broker=broker,
                                                 broker_account_name="broker_acocunt",
                                                 account_type=BrokerAccount.AccountType.LIVE)
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(CashPositions(), []))
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(
            return_value=BrokerMarginRequirements(0, 0, 1000, 1000, 1000))

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)

        self.assertEqual(0, service.get_margin_detail(company, date).margin_requirement)
        detail = service.get_margin_detail(company=company, date=date)
        hedge_position_service.get_cash_positions.assert_called_with(company=company, date=date)
        self.assertEqual(0, detail.margin_requirement)
        self.assertEqual(1000, detail.excess_liquidity)
        self.assertEqual(company, detail.company)
        self.assertEqual(date, detail.date)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_single_position_no_additional_cash(self,
                                                margin_calculator,
                                                broker_margin_service,
                                                margin_rates_cache_provider,
                                                cash_flow_provider,
                                                fx_spot_provider,
                                                hedge_position_service,
                                                margin_detail_service,
                                                pnl_calculator,
                                                deposit_service):
        """
        Test that we can calculate margin when we have a single position with no additional cash.
        """
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        _ = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        cash_positions = MyCashPositions(cash_by_currency={USD: 110, EUR: 100})
        broker_margin_requirement = BrokerMarginRequirements(0, 0, 0, 0, 0)
        spot_fx_cache = DictSpotFxCache(date=date, spots={"EUR/USD": 1.05, "USD/EUR": 1 / 1.05})
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(cash_positions, []))
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(return_value=broker_margin_requirement)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        fx_spot_provider.get_spot_cache = mock.MagicMock(return_value=spot_fx_cache)
        margin_rates_cache_provider.get_margin_rates_cache = mock.MagicMock(return_value=margin_rates)
        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        margin_calculator.compute_margin = mock.MagicMock(return_value=100)
        detail = service.get_margin_detail(company=company, date=date)
        hedge_position_service.get_cash_positions.assert_called_with(company=company, date=date)
        margin_calculator.compute_margin.assert_called_with(cash_positions=cash_positions,
                                                            domestic=cny,
                                                            spot_fx_cache=spot_fx_cache,
                                                            margin_rates=margin_rates,
                                                            multiplier=2.0)
        self.assertEqual(100, detail.margin_requirement)
        self.assertEqual(-100, detail.excess_liquidity)
        self.assertEqual(company, detail.company)
        self.assertEqual(date, detail.date)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_single_position_with_additional_cash(self,
                                                  margin_calculator,
                                                  broker_margin_service,
                                                  margin_rates_cache_provider,
                                                  cash_flow_provider,
                                                  fx_spot_provider,
                                                  hedge_position_service,
                                                  margin_detail_service,
                                                  pnl_calculator,
                                                  deposit_service):
        """
        Test that we can calculate margin when we have a single position with no additional cash.
        """
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        _ = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        cash_positions = MyCashPositions(cash_by_currency={USD: 110, EUR: 100})
        broker_margin_requirement = BrokerMarginRequirements(0, 0, 0, 100, 100)
        spot_fx_cache = DictSpotFxCache(date=date, spots={"EUR/USD": 1.05, "USD/EUR": 1 / 1.05})
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        hedge_position_service.get_cash_positions = mock.MagicMock(return_value=(cash_positions, []))
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(return_value=broker_margin_requirement)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        fx_spot_provider.get_spot_cache = mock.MagicMock(return_value=spot_fx_cache)
        margin_rates_cache_provider.get_margin_rates_cache = mock.MagicMock(return_value=margin_rates)
        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        margin_calculator.compute_margin = mock.MagicMock(return_value=100)
        detail = service.get_margin_detail(company=company, date=date)
        hedge_position_service.get_cash_positions.assert_called_with(company=company, date=date)
        cash_positions_with_additional_cash = MyCashPositions(cash_by_currency={USD: 210, EUR: 100})
        margin_calculator.compute_margin.assert_called_with(cash_positions=cash_positions_with_additional_cash,
                                                            domestic=cny,
                                                            spot_fx_cache=spot_fx_cache,
                                                            margin_rates=margin_rates,
                                                            multiplier=2.0)
        self.assertEqual(100, detail.margin_requirement)
        self.assertEqual(0, detail.excess_liquidity)
        self.assertEqual(company, detail.company)
        self.assertEqual(date, detail.date)


# noinspection DuplicatedCode
class TestProjectedMargin(TestCase):



    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_broker_account(self,
                               margin_calculator,
                               broker_margin_service,
                               margin_rates_cache_provider,
                               cash_flow_provider,
                               fx_spot_provider,
                               hedge_position_service,
                               margin_detail_service,
                               pnl_calculator,
                               deposit_service):
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        _ = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=None)

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margin = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)

        self.assertEqual([], projected_margin)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_active_accounts(self,
                                margin_calculator,
                                broker_margin_service,
                                margin_rates_cache_provider,
                                cash_flow_provider,
                                fx_spot_provider,
                                hedge_position_service,
                                margin_detail_service,
                                pnl_calculator,
                                deposit_service):
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        account = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        account.is_active = False
        account.save()
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margin = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)

        self.assertEqual([], projected_margin)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_hedge_settings(self,
                               margin_calculator,
                               broker_margin_service,
                               margin_rates_cache_provider,
                               cash_flow_provider,
                               fx_spot_provider,
                               hedge_position_service,
                               margin_detail_service,
                               pnl_calculator,
                               deposit_service):
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        account = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        account.is_active = True
        account.save()
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margin = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)

        self.assertEqual([], projected_margin)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_no_cashflows(self,
                          margin_calculator,
                          broker_margin_service,
                          margin_rates_cache_provider,
                          cash_flow_provider,
                          fx_spot_provider,
                          hedge_position_service,
                          margin_detail_service,
                          pnl_calculator,
                          deposit_service):
        date = Date.today()
        _, cny = Currency.create_currency('USD', 'USD', 'USD')
        _, broker = Broker.create_broker("TEST_BROKER")
        company = Company.objects.create(name='Test Company', currency=cny, status=Company.CompanyStatus.ACTIVE)
        company.save()
        _ = Account.objects.create(name='Test Account', company=company, type=Account.AccountType.DEMO)
        account = Account.objects.create(name='Live Account', company=company, type=Account.AccountType.LIVE)
        account.is_active = True
        account.save()
        _ = HedgeSettings.create_or_update_settings(account=account, margin_budget=100000)
        _, broker_account = BrokerAccount.create_account_for_company(company=company,
                                                                     broker=broker,
                                                                     broker_account_name="broker_acocunt",
                                                                     account_type=BrokerAccount.AccountType.LIVE)

        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        cash_flow_provider.get_projected_raw_cash_exposures = mock.MagicMock(return_value=[])

        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margin = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)

        self.assertEqual([], projected_margin)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_single_cashflow_exposure_in_domestic(self,
                                                  margin_calculator,
                                                  broker_margin_service,
                                                  margin_rates_cache_provider,
                                                  cash_flow_provider,
                                                  fx_spot_provider,
                                                  hedge_position_service,
                                                  margin_detail_service,
                                                  pnl_calculator,
                                                  deposit_service):
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
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        margin_rates_cache_provider.get_margin_rates_cache = mock.MagicMock(return_value=margin_rates)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(
            return_value=BrokerMarginRequirements(0, 0, 0, 0, 0))
        exposures: List[Tuple[Date, List[Tuple[Currency, float]]]] = [
            (Date.from_datetime_date(date + 1), [(usd, 1000.0)])]
        cash_flow_provider.get_projected_raw_cash_exposures = mock.MagicMock(return_value=exposures)
        margin_calculator.compute_margin_from_vfx = mock.MagicMock(return_value=1000.0)
        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margins = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)
        self.assertEqual(1, len(projected_margins))
        projected_margin = projected_margins[0]
        self.assertEqual(Date.from_datetime_date(date + 1), projected_margin.date)
        self.assertEqual(0.0, projected_margin.amount_before_deposit)
        self.assertEqual(0.0, projected_margin.amount_after_deposit)
        self.assertEqual(0, projected_margin.excess)
        self.assertEqual(1000.0, projected_margin.total_hedge)

    @mock.patch("main.apps.margin.services.calculators.MarginCalculator")
    @mock.patch("main.apps.margin.services.broker_margin_service.BrokerMarginServiceInterface")
    @mock.patch("main.apps.margin.services.margin_service.MarginRatesCacheProvider")
    @mock.patch("main.apps.account.services.cashflow_provider.CashFlowProviderInterface")
    @mock.patch("main.apps.marketdata.services.fx.fx_provider.FxSpotProvider")
    @mock.patch("main.apps.hedge.services.hedge_position.HedgePositionService")
    @mock.patch("main.apps.margin.services.margin_detail_service.MarginDetailServiceInterface")
    @mock.patch("hdlib.Utils.PnLCalculator.PnLCalculator")
    @mock.patch("main.apps.margin.services.DepositService")
    def test_single_cashflow_exposure(self,
                                      margin_calculator,
                                      broker_margin_service,
                                      margin_rates_cache_provider,
                                      cash_flow_provider,
                                      fx_spot_provider,
                                      hedge_position_service,
                                      margin_detail_service,
                                      pnl_calculator,
                                      deposit_service):
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
        fx_spot_provider.get_spot_cache = mock.MagicMock(return_value=spot_fx_cache)
        margin_rates = MarginRatesCache(broker=broker, spot_fx_cache=spot_fx_cache, margin={("EUR", "USD"): 0.025,
                                                                                            ("USD", "EUR"): 0.025})
        margin_rates_cache_provider.get_margin_rates_cache = mock.MagicMock(return_value=margin_rates)
        broker_margin_service.get_broker_for_company = mock.MagicMock(return_value=broker_account)
        broker_margin_service.get_broker_margin_summary = mock.MagicMock(
            return_value=BrokerMarginRequirements(0, 0, 0, 0, 0))
        exposures: List[Tuple[Date, List[Tuple[Currency, float]]]] = [
            (Date.from_datetime_date(date + 1), [(eur, 1000.0)])]
        cash_flow_provider.get_projected_raw_cash_exposures = mock.MagicMock(return_value=exposures)
        margin_calculator.compute_margin_from_vfx = mock.MagicMock(return_value=1000.0)
        service = MarginProviderService(margin_calculator=margin_calculator,
                                        broker_service=broker_margin_service,
                                        margin_rates_cache_provider=margin_rates_cache_provider,
                                        cash_provider_service=cash_flow_provider,
                                        fx_spot_provider=fx_spot_provider,
                                        hedge_position_service=hedge_position_service,
                                        margin_detail_service=margin_detail_service,
                                        margin_multiplier=2.0,
                                        pnl_calculator=pnl_calculator,
                                        deposit_service=deposit_service)
        additional_cash = {}
        projected_margins = service.compute_projected_margin(
            date=date,
            company=company,
            account_type=Account.AccountType.LIVE,
            additional_cash=additional_cash,
            days_to_project=30)

        self.assertEqual(1, len(projected_margins))
        projected_margin = projected_margins[0]
        self.assertEqual(Date.from_datetime_date(date + 1), projected_margin.date)
        self.assertEqual(1000.0, projected_margin.amount_before_deposit)
        self.assertEqual(1000.0, projected_margin.amount_after_deposit)
        self.assertEqual(-1000, projected_margin.excess)
        self.assertEqual(1000.0 * 1.05, projected_margin.total_hedge)
