from typing import Optional, Tuple, Sequence

from main.apps.currency.models import FxPair, FxPairTypes
from main.apps.util import ActionStatus, get_or_none

from django.db import models


class FxMarketConvention(models.Model):
    """
    Table that records which FX pairs actually trade.
    """
    # An FX pair that actively trades.
    pair = models.OneToOneField(FxPair, on_delete=models.CASCADE, null=False, unique=True)

    # The minimum lot size for this FX pair. Note that this is technically broker dependent, but right now we only
    # have one broker.
    min_lot_size = models.FloatField(null=False)

    # An indicator of if this fx pair is actually fully supported / setup in the system
    # The broker may allow trading in Fx pairs, but these pairs are not setup in the system (e.g. no history)
    is_supported = models.BooleanField(null=False)

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_conventions(is_supported_only: bool = False) -> Sequence:
        if is_supported_only:
            return FxMarketConvention.objects.filter(**{'is_supported': True})

        return FxMarketConvention.objects.all()

    @staticmethod
    @get_or_none
    def get_convention(pair: FxPairTypes) -> Optional['FxMarketConvention']:
        pair_ = FxPair.get_pair(pair)
        if pair_ is None:
            raise ValueError(f"could not find FX pair {pair}")
        return FxMarketConvention.objects.get(pair=pair_)

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def create_or_update_traded_pair(fx_pair: FxPairTypes,
                                     min_lot_size: float = 1000,
                                     is_supported: bool = True
                                     ) -> Tuple[ActionStatus, Optional['FxMarketConvention']]:
        fx_pair_ = FxPair.get_pair(pair=fx_pair)
        if not fx_pair_:
            return ActionStatus.error(f"The Fx Pair {fx_pair} doesnt exist"), None

        try:
            fxpair, created = FxMarketConvention.objects.update_or_create(pair=fx_pair_,
                                                                          defaults={"min_lot_size": min_lot_size,
                                                                                    "is_supported": is_supported})
        except Exception as ex:
            return ActionStatus.error(f"Exception updating or creating: {ex}"), fx_pair
        if not created:
            return ActionStatus.success(f"Updated existing convention"), fxpair

        return ActionStatus.success(f"Created new convention"), fxpair
