from main.apps.ibkr.models import SupportedFxPair


class IbkrProviderHandlerMixin:
    def get_supported_pairs(self):
        return SupportedFxPair.get_ibkr_supported_pairs()
