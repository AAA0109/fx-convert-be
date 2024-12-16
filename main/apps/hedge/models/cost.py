from auditlog.registry import auditlog
from django.db import models

from django.core.validators import MinValueValidator

from typing import Sequence, Tuple, Optional, Dict

from hdlib.DateTime import Date
from main.apps.currency.models import FxPair
from main.apps.marketdata.models import Fx, DataCut
from main.apps.broker.models.broker import Broker

import logging

logger = logging.getLogger(__name__)


class FxBrokerData(Fx):
    """ Base model for Fx data that is tied to a broker, e.g. margin rates """
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True


class FxSpotCommission(FxBrokerData):
    """ Model for the rate of commission for FX purchase / sale, depending on the broker """

    class Meta:
        verbose_name_plural = "fxspotcommissions"
        unique_together = (("pair", "data_cut", "broker"),)

    # Commission rate per unit of fx
    rate = models.FloatField(null=False, validators=[MinValueValidator(0.0)])

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_rates(date: Date,
                  broker: Broker,
                  fx_pairs: Optional[Sequence[FxPair]] = None) -> Tuple[Dict[FxPair, float], Dict[FxPair, DataCut]]:
        filters = {"broker": broker, "data_cut__cut_time__gt": (date - 5), "data_cut__cut_time__lte": date}
        commissions = FxSpotCommission.objects.filter(**filters)

        if fx_pairs:
            filters["pair__in"] = fx_pairs

        rates, cuts = {}, {}
        for commission in commissions:
            pair = commission.pair

            # Use the most up to date information.
            if pair not in rates or cuts[pair].cut_time < commission.data_cut.cut_time:
                rates[pair] = commission.rate
                cuts[pair] = commission.data_cut

        return rates, cuts

auditlog.register(FxSpotCommission)

class FxSpotSpread(FxBrokerData):
    """ Model for the spot bid/ask spread rate for FX spot transaction, depending on the broker"""

    class Meta:
        verbose_name_plural = "fxspotspreads"
        unique_together = (("pair", "data_cut", "broker"),)

    # Bid/Ask spread on the FX spot rate
    spread = models.FloatField(null=False, validators=[MinValueValidator(0.0)])

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_spreads(date: Date,
                    broker: Broker,
                    fx_pairs: Optional[Sequence[FxPair]] = None) -> Tuple[Dict[FxPair, float], Dict[FxPair, DataCut]]:
        filters = {"broker": broker, "data_cut__cut_time__gt": (date - 5), "data_cut__cut_time__lte": date}
        spot_spreads = FxSpotSpread.objects.filter(**filters).prefetch_related().select_related()
        if fx_pairs:
            filters["pair__in"] = fx_pairs

        spreads, cuts = {}, {}
        for spread in spot_spreads:
            pair = spread.pair

            # Use the most up-to-date information.
            if pair not in spreads or cuts[pair].cut_time < spread.data_cut.cut_time:
                spreads[pair] = spread.spread
                cuts[pair] = spread.data_cut

        return spreads, cuts

auditlog.register(FxSpotSpread)
