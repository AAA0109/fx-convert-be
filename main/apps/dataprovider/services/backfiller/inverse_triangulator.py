import logging
from main.apps.core.models.config import Config
from main.apps.currency.models.currency import Currency
from main.apps.dataprovider.models.dataprovider import DataProvider
from main.apps.dataprovider.models.profile import Profile
from main.apps.dataprovider.services.backfiller.inverse_triangulate_handler.corpay.forward import CorpayForwardInverseTriangulateHandler
from main.apps.dataprovider.services.backfiller.inverse_triangulate_handler.corpay.spot import CorpaySpotInverseTriangulateHandler


class InverseAndTriangulatorService(object):
    FXPAIR_HOME_CURRENCIES_PATH = 'system/fxpair/home_currencies'
    profile: Profile
    home_currency: Currency

    def __init__(self, profile_id: int, home_currency: str = 'USD') -> None:
        self.profile = Profile.objects.filter(
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False,
            id=profile_id
        ).first()
        self.home_currency = Currency.get_currency(currency=home_currency)

    def execute(self):
        logging.info(f"Starting inverse and triangulation for profile: {self.profile.pk}")
        source = self.profile.source
        data_provider = source.data_provider
        target = self.profile.target

        if data_provider.provider_handler == DataProvider.ProviderHandlers.CORPAY:
            corpay_home_currency_config = Config.get_config(path=self.FXPAIR_HOME_CURRENCIES_PATH)

            if corpay_home_currency_config:
                self.home_currency = Currency.get_currency(currency=corpay_home_currency_config.value[0])

            if target.model in ['corpayfxspot']:
                corpay_fx_spot_handler = CorpaySpotInverseTriangulateHandler(model=target.model_class(), home_currency=self.home_currency)
                corpay_fx_spot_handler.execute()
            elif target.model in ['corpayfxforward']:
                corpay_fx_forward_handler = CorpayForwardInverseTriangulateHandler(model=target.model_class(), home_currency=self.home_currency)
                corpay_fx_forward_handler.execute()

