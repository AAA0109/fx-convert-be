from typing import List, Optional

from django.db.models import Model, QuerySet
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.dataclasses.marketdata import FwdPoints, FxRates
from main.apps.dataprovider.services.backfiller.inverse_triangulate_handler.corpay.base import CorpayInverseTriangulationHandler
from main.apps.marketdata.models.fx.rate import CorpayFxForward, CorpayFxSpot


class CorpayForwardInverseTriangulateHandler(CorpayInverseTriangulationHandler):
    home_currency_based_data: QuerySet[CorpayFxForward]
    inverse_home_currency_based_data: List[CorpayFxForward]
    spot_data = QuerySet[CorpayFxSpot]

    def __init__(self, model: Model, home_currency: Currency) -> None:
        super().__init__(model, home_currency)
        self.spot_data = CorpayFxSpot.objects.filter(
            data_cut=self.latest_datacut)

    def calculate_forward_points(self, rates: FxRates, pair: FxPair) -> Optional[FwdPoints]:
        spot_rate = self.spot_data.filter(pair=pair).first()
        if not spot_rate:
            return None

        return FwdPoints(
            fwd_points=rates.rate - spot_rate.rate,
            fwd_points_ask=rates.rate_ask - spot_rate.rate_ask,
            fwd_points_bid=rates.rate_bid - spot_rate.rate_bid,
        )

    def is_pair_tenor_exist(self, fxdata: CorpayFxForward, list_fxdata: List[CorpayFxForward]) -> bool:
        for data in list_fxdata:
            if fxdata.pair == data.pair and fxdata.tenor == data.tenor:
                return True
        return False

    def create_fxdata(self, pair: FxPair, rates: FxRates, fwd_points: FwdPoints, ref_fxdata: CorpayFxForward) -> CorpayFxForward:
        return CorpayFxForward(
            date=self.latest_datacut.cut_time,
            data_cut=self.latest_datacut,
            pair=pair,
            rate=rates.rate,
            rate_ask=rates.rate_ask,
            rate_bid=rates.rate_bid,
            fwd_points=fwd_points.fwd_points,
            fwd_points_bid=fwd_points.fwd_points_bid,
            fwd_points_ask=fwd_points.fwd_points_ask,
            tenor=ref_fxdata.tenor,
            tenor_days=ref_fxdata.tenor_days
        )

    def populate_inverse_data(self) -> List[CorpayFxForward]:
        inverse_data: List[CorpayFxForward] = []
        for home_base_fx in self.home_currency_based_data:
            inverse_pair = FxPair.get_inverse_pair(pair=home_base_fx.pair)
            rates = self.calculate_inverse_rates(marketdata=home_base_fx)
            fwd_points: FwdPoints = self.calculate_forward_points(
                rates=rates, pair=inverse_pair)
            if fwd_points:
                inverse_data.append(self.create_fxdata(
                    pair=inverse_pair, rates=rates, fwd_points=fwd_points, ref_fxdata=home_base_fx))
        return inverse_data

    def populate_triangulate_data(self) -> List[CorpayFxForward]:
        triangulate_data: List[CorpayFxForward] = []

        for inverse_home_base_fx in self.inverse_home_currency_based_data:
            for home_base_fx in self.home_currency_based_data:
                if inverse_home_base_fx.pair.base_currency != home_base_fx.pair.quote_currency and inverse_home_base_fx.tenor == home_base_fx.tenor:
                    pair = FxPair.get_pair_from_currency(
                        base_currency=inverse_home_base_fx.pair.base_currency, quote_currency=home_base_fx.pair.quote_currency)
                    rates = self.calculate_triangulate_rates(inverse_home_base_fx=inverse_home_base_fx, home_base_fx=home_base_fx)

                    fwd_points: FwdPoints = self.calculate_forward_points(
                        rates=rates, pair=pair)

                    if fwd_points:
                        triangulatedfx = self.create_fxdata(
                            pair=pair, rates=rates, fwd_points=fwd_points, ref_fxdata=home_base_fx)

                        if not self.is_pair_tenor_exist(fxdata=triangulatedfx, list_fxdata=triangulate_data):
                            triangulate_data.append(triangulatedfx)

                        inverse_pair = FxPair.get_inverse_pair(pair=pair)
                        inverse_rates = self.calculate_inverse_rates(
                            marketdata=triangulatedfx)
                        inverse_fwd_points: FwdPoints = self.calculate_forward_points(
                            rates=inverse_rates, pair=inverse_pair)
                        inversed_triangulatedfx = self.create_fxdata(
                            pair=inverse_pair, rates=inverse_rates, fwd_points=inverse_fwd_points, ref_fxdata=home_base_fx)

                        if not self.is_pair_tenor_exist(fxdata=inversed_triangulatedfx, list_fxdata=triangulate_data):
                            triangulate_data.append(inversed_triangulatedfx)

        return triangulate_data

    def get_pk_field_names(self) -> List[str]:
        return ['data_cut', 'pair', 'tenor']
