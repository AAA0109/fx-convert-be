from main.apps.dataprovider.services.profile.provider.base import BaseProvider
from main.apps.ibkr.models import SupportedFxPair


class IBKRSpotFxPairProvider(BaseProvider):
    def get_ids(self):
        qs = SupportedFxPair.get_ibkr_supported_pairs()
        return list(qs.values_list('id', flat=True))
