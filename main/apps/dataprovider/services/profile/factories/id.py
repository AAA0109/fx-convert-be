from main.apps.core.models.config import Config
from main.apps.dataprovider.models import DataProvider
from main.apps.dataprovider.models.profile import ProfileParallelOption
from main.apps.dataprovider.services.profile.provider.id.corpay import CorpayFxPairSpotProvider, \
    CorpayFxForwardProvider, CorpayCompanyProvider
from main.apps.dataprovider.services.profile.provider.id.ibkr import IBKRSpotFxPairProvider


class ParallelIdGeneratorFactory:
    FXPAIR_HOME_CURRENCIES_PATH = 'system/fxpair/home_currencies'

    def __init__(self) -> None:
        self.corpay_base_currency = Config.get_config(path=self.FXPAIR_HOME_CURRENCIES_PATH).value[0]

    def generate_dynamic_ids(self, parallel_option: ProfileParallelOption):
        id_provider = None
        if parallel_option.type != ProfileParallelOption.Type.DYNAMIC:
            raise ValueError("Profile Parallel Option is not dynamic")
        provider_handler = parallel_option.profile.source.data_provider.provider_handler

        if parallel_option.provider == ProfileParallelOption.Provider.FXPAIR:
            if provider_handler == DataProvider.ProviderHandlers.IBKR:
                if parallel_option.instrument == ProfileParallelOption.Instrument.SPOT:
                    id_provider = IBKRSpotFxPairProvider()
            if provider_handler == DataProvider.ProviderHandlers.CORPAY:
                if parallel_option.instrument == ProfileParallelOption.Instrument.SPOT:
                    id_provider = CorpayFxPairSpotProvider(base_currency=self.corpay_base_currency)
                if parallel_option.instrument == ProfileParallelOption.Instrument.FORWARD:
                    id_provider = CorpayFxForwardProvider(base_currency=self.corpay_base_currency)
        if parallel_option.provider == ProfileParallelOption.Provider.COMPANY:
            if provider_handler == DataProvider.ProviderHandlers.CORPAY:
                id_provider = CorpayCompanyProvider()

        if id_provider is not None:
            return id_provider.get_ids()
        return []
