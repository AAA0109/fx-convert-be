from typing import List

from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.dataclasses.marketdata import FxRates
from main.apps.dataprovider.services.backfiller.inverse_triangulate_handler.corpay.base import CorpayInverseTriangulationHandler
from main.apps.marketdata.models.fx.rate import CorpayFxSpot


class CorpaySpotInverseTriangulateHandler(CorpayInverseTriangulationHandler):
    home_currency_based_data: List[CorpayFxSpot]
    inverse_home_currency_based_data: List[CorpayFxSpot]

    def is_pair_exist(self, fxdata: CorpayFxSpot, list_fxdata: List[CorpayFxSpot]) -> bool:
        for data in list_fxdata:
            if fxdata.pair == data.pair:
                return True
        return False

    def create_fxdata(self, pair: FxPair, rates: FxRates) -> CorpayFxSpot:
        return CorpayFxSpot(
            date=self.latest_datacut.cut_time,
            data_cut=self.latest_datacut,
            pair=pair,
            rate=rates.rate,
            rate_ask=rates.rate_ask,
            rate_bid=rates.rate_bid
        )

    def populate_inverse_data(self) -> List[CorpayFxSpot]:
        inverse_data: List[CorpayFxSpot] = []
        for home_base_fx in self.home_currency_based_data:
            pair=FxPair.get_inverse_pair(pair=home_base_fx.pair)
            inverse_rates = self.calculate_inverse_rates(marketdata=home_base_fx)
            inverse_data.append(self.create_fxdata(pair=pair, rates=inverse_rates))
        return inverse_data

    def populate_triangulate_data(self) -> List[CorpayFxSpot]:
        triangulate_data: List[CorpayFxSpot] = []
        for inverse_home_base_fx in self.inverse_home_currency_based_data:
            for home_base_fx in self.home_currency_based_data:
                if inverse_home_base_fx.pair.base_currency != home_base_fx.pair.quote_currency:
                    pair = FxPair.get_pair_from_currency(
                        base_currency=inverse_home_base_fx.pair.base_currency, quote_currency=home_base_fx.pair.quote_currency)

                    rates = self.calculate_triangulate_rates(inverse_home_base_fx=inverse_home_base_fx, home_base_fx=home_base_fx)
                    triangulatedfx = self.create_fxdata(pair=pair, rates=rates)

                    if not self.is_pair_exist(fxdata=triangulatedfx, list_fxdata=triangulate_data):
                        triangulate_data.append(triangulatedfx)

                    inverse_pair = FxPair.get_inverse_pair(pair=pair)
                    inverse_rates = self.calculate_inverse_rates(marketdata=triangulatedfx)

                    inverse_triangulatedfx = self.create_fxdata(pair=inverse_pair, rates=inverse_rates)
                    if not self.is_pair_exist(fxdata=inverse_triangulatedfx, list_fxdata=triangulate_data):
                        triangulate_data.append(inverse_triangulatedfx)

        return triangulate_data
