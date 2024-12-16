import unittest

from main.apps.account.api.test import BaseTestCase
from main.apps.marketdata.services.fx.fx_market_convention_service import *
from main.apps.currency.models.fxpair import FxPair


class FxMarketConventionService_TestClass(FxMarketConventionService):
    # def _get_convention(self, fx_pair: FxPairTypes) -> FxMarketConvention:
    #     convention = FxMarketConvention()
    #     convention.pair = self._get_pair(fx_pair)
    #     convention.min_lot_size = 150
    #     return convention
    pass


class FxMarketConventionServiceTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

        self.euro_usd = FxPair.get_pair("EUR/USD")
        self.usd_gbp = FxPair.get_pair("USD/GBP")
        self.gbp_usd = FxPair.get_pair("GBP/USD")
        self.gbp_eur = FxPair.get_pair("GBP/EUR")
        self.usd_cny = FxPair.get_pair("USD/CNY")

        convention = FxMarketConvention()
        convention.pair = self.euro_usd
        convention.min_lot_size = 150
        convention.is_supported = True
        convention.save()
        self.eur_usd_conv = convention

        convention = FxMarketConvention()
        convention.pair = self.usd_gbp
        convention.min_lot_size = 500
        convention.is_supported = True
        convention.save()
        self.usd_gbp_conv = convention

        # Add a pair that is NOT supported
        convention = FxMarketConvention()
        convention.pair = self.usd_cny
        convention.min_lot_size = 500
        convention.is_supported = False
        convention.save()
        self.usd_cny_conv = convention

    def tearDown(self):
        self.eur_usd_conv.delete()
        self.usd_gbp_conv.delete()
        self.usd_cny_conv.delete()
        super().tearDown()

    def test_is_market_traded(self):
        service = FxMarketConventionService_TestClass()
        converter = service.make_fx_market_converter(is_hedge_supported_only=True)

        self.assertTrue(converter.is_market_traded_pair(self.euro_usd))
        self.assertTrue(converter.is_market_traded_pair(self.usd_gbp))
        self.assertFalse(converter.is_market_traded_pair(self.gbp_usd))
        self.assertFalse(converter.is_market_traded_pair(self.gbp_eur))
        self.assertFalse(converter.is_market_traded_pair(self.usd_cny))

    def test_is_market_traded_but_not_necessarily_supported(self):
        service = FxMarketConventionService_TestClass()
        converter = service.make_fx_market_converter(is_hedge_supported_only=False)

        self.assertTrue(converter.is_market_traded_pair(self.euro_usd))
        self.assertTrue(converter.is_market_traded_pair(self.usd_gbp))
        self.assertFalse(converter.is_market_traded_pair(self.gbp_usd))
        self.assertFalse(converter.is_market_traded_pair(self.gbp_eur))
        self.assertTrue(converter.is_market_traded_pair(self.usd_cny))

    def test_convention(self):
        service = FxMarketConventionService_TestClass()
        converter = service.make_fx_market_converter()

        self.assertEqual(150, converter.get_lot_size(self.euro_usd))
        self.assertEqual(500, converter.get_lot_size(self.usd_gbp))

    def test_rounding(self):
        service = FxMarketConventionService_TestClass()

        converter = service.make_fx_market_converter(is_hedge_supported_only=True)

        self.assertEqual(150, converter.round_to_lot(self.euro_usd, 150))
        self.assertEqual(150, converter.round_to_lot(self.euro_usd, 180.5))
        self.assertEqual(0, converter.round_to_lot(self.euro_usd, 149.5))
        self.assertEqual(500, converter.round_to_lot(self.usd_gbp, 800.30))
        self.assertEqual(1000, converter.round_to_lot(self.usd_gbp, 1010.))


if __name__ == '__main__':
    unittest.main()
