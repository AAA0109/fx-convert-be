from abc import abstractmethod
from typing import List, Union
from django.db.models import Model

from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.dataclasses.marketdata import FxRates
from main.apps.dataprovider.services.backfiller.inverse_triangulate_handler.handler import InverseAndTriangulateHandler
from main.apps.marketdata.models.fx.rate import CorpayFxForward, CorpayFxSpot
from main.apps.marketdata.models.marketdata import DataCut


class CorpayInverseTriangulationHandler(InverseAndTriangulateHandler):
    latest_datacut: DataCut
    home_currency_based_data: List[Model]
    inverse_home_currency_based_data: List[Model]

    def __init__(self, model: Model, home_currency: Currency) -> None:
        super().__init__(model, home_currency)
        latest_data: Union[CorpayFxSpot, CorpayFxForward] = self.model.objects.order_by('-data_cut_id').first()
        self.latest_datacut = latest_data.data_cut
        self.home_currency_based_data = self.model.objects.filter(data_cut=self.latest_datacut, pair__base_currency=self.home_currency)

    def get_pk_field_names(self) -> List[str]:
        return ['data_cut', 'pair']

    def calculate_inverse_rates(self, marketdata: Union[CorpayFxSpot, CorpayFxForward]) -> FxRates:
        return FxRates(
            rate=1/marketdata.rate,
            rate_ask=1/marketdata.rate_bid,
            rate_bid=1/marketdata.rate_ask
        )

    def calculate_triangulate_rates(self, home_base_fx: Union[CorpayFxSpot, CorpayFxForward], inverse_home_base_fx: Union[CorpayFxSpot, CorpayFxForward]) -> FxRates:
        # check for aaahome * bbbhome
        if inverse_home_base_fx.pair.quote_currency == home_base_fx.pair.quote_currency:
            inverse_rates = self.calculate_inverse_rates(marketdata=home_base_fx)
            return FxPair(
                rate=inverse_home_base_fx.rate * inverse_rates.rate,
                rate_ask=inverse_home_base_fx.rate_ask * inverse_rates.rate_ask,
                rate_bid=inverse_home_base_fx.rate_bid * inverse_rates.rate_bid
            )
        # check for homeaaa * homebbb
        elif inverse_home_base_fx.pair.base_currency == home_base_fx.pair.base_currency:
            inverse_rates = self.calculate_inverse_rates(marketdata=inverse_home_base_fx)
            return FxPair(
                rate=inverse_rates.rate * home_base_fx.rate,
                rate_ask=inverse_rates.rate_ask * home_base_fx.rate_ask,
                rate_bid=inverse_rates.rate_bid * home_base_fx.rate_bid
            )

        # immediately calculate for pair aaahome * homebbb
        return FxRates(
            rate=inverse_home_base_fx.rate * home_base_fx.rate,
            rate_ask=inverse_home_base_fx.rate_ask * home_base_fx.rate_ask,
            rate_bid=inverse_home_base_fx.rate_bid * home_base_fx.rate_bid
        )

    @abstractmethod
    def create_fxdata(self, pair: FxPair, rates: FxRates) -> Model:
        raise NotImplementedError
