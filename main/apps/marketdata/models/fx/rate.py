from typing import Union, Sequence, Optional, Tuple

import numpy as np
from django.db import models
from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.DateTime.Date import Date

from main.apps.currency.models.fxpair import FxPair, FxPairId, FxPairName, FxPairTypes
from main.apps.marketdata.support.TenorConverter import TenorConverter
from main.apps.util import ActionStatus
from . import Fx
# Define a type for all the ways that we can indicate an Fx pair and translate it via FxPair.get_pair.
from ..marketdata import DataCut

FxTypes = Union[FxPair, FxPairInterface, FxPairHDL, FxPairName, FxPairId, tuple]


class AbstractFxSpot(Fx):
    rate = models.FloatField(null=True)
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    class Meta:
        abstract = True
        unique_together = (("data_cut", "pair"),)


class FxSpot(AbstractFxSpot):

    @staticmethod
    def get_spot_ts(fxpair: FxPairTypes,
                    start_date: Optional[Date] = None,
                    end_date: Optional[Date] = None):
        fxpair_ = FxPair.get_pair(fxpair)
        if fxpair_ is None:
            raise RuntimeError(f"could not find")

        filters = {"pair": fxpair_}
        if start_date:
            filters["data_cut__cut_time__gte"] = start_date
        if end_date:
            filters["data_cut__cut_time__lte"] = end_date
        fxspot_objects = FxSpot.objects.filter(**filters).order_by("data_cut__cut_time")

        times, spots = [], []
        for spot in fxspot_objects:
            times.append(Date.from_datetime(spot.data_cut.cut_time))
            spots.append(spot.rate)

        return np.array(times), np.array(spots)

    @staticmethod
    def get_spot(fxpair: FxPairTypes, date: Date) -> Optional[Tuple[float, Date]]:
        """
        Get the most recent fx spot for a particular date.
        """
        fxpair_ = FxPair.get_pair(fxpair)
        if fxpair_ is None:
            return None
        spot = FxSpot.objects.filter(pair=fxpair_, date__lte=date).order_by("-date").first()
        if spot:
            return spot.rate, Date.from_datetime(spot.date)
        return None

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def add_spot(data_cut: DataCut,
                 pair: FxTypes,
                 rate: float,
                 bid_rate: Optional[float] = None,
                 ask_rate: Optional[float] = None,
                 overwrite: bool = False) -> Tuple[ActionStatus, Optional['FxSpot']]:
        """
        Add a spot to the database for a particular FX pair on a particular date. If the spot already exists, it will
        not be overwritten unless the overwrite flag is true.
        """
        create = FxSpot.objects.create if overwrite else FxSpot.objects.get_or_create
        pair_ = FxPair.get_pair(pair)
        if pair_ is None:
            return ActionStatus.error(f"FX pair {pair} does not exist, cannot create pair"), None
        fxspot, created = create(date=data_cut.date,
                                 data_cut=data_cut,
                                 pair=pair_,
                                 rate=rate,
                                 rate_bid=bid_rate,
                                 rate_ask=ask_rate)
        if not created:
            return ActionStatus.no_change(f"Did not create spot for {pair} on {data_cut.cut_time}, already exists"), \
                fxspot

        return ActionStatus.success(f"Added spot for {pair}, data cut {data_cut.id}, time {data_cut.cut_time}, "
                                    f"value = {rate} (bid = {bid_rate}, ask = {ask_rate})"), fxspot


class FxSpotIntra(AbstractFxSpot):
    data_cut = None

    class Meta:
        unique_together = (("date", "pair"),)


class FxSpotIntraIBKR(AbstractFxSpot):
    data_cut = None

    class Meta:
        unique_together = (("date", "pair"),)


class AbstractFxSpotRange(Fx):
    # Open prices (nullable)
    open = models.FloatField(null=True)
    open_bid = models.FloatField(null=True)
    open_ask = models.FloatField(null=True)

    # Low prices (nullable)
    low = models.FloatField(null=True)
    low_bid = models.FloatField(null=True)
    low_ask = models.FloatField(null=True)

    # High prices (nullable)
    high = models.FloatField(null=True)
    high_bid = models.FloatField(null=True)
    high_ask = models.FloatField(null=True)

    # Close prices (nullable)
    close = models.FloatField(null=True)
    close_bid = models.FloatField(null=True)
    close_ask = models.FloatField(null=True)

    class Meta:
        abstract = True
        unique_together = (("data_cut", "pair"),)


class FxSpotRange(AbstractFxSpotRange):
    pass


class AbstractFxForward(Fx):
    """
    Fx Forward model, represents the Fx forward curve tenors per FX pair on a given date
    """
    tenor = models.CharField(max_length=4, null=False)
    interest_days = models.IntegerField(null=True, verbose_name="Interest Days",
                                        help_text="Day count for a forward from spot to delivery based on tenor.")
    delivery_days = models.IntegerField(null=True, verbose_name="Delivery Days",
                                        help_text="Day count from spot to delivery date for an option based on tenor.")
    expiry_days = models.IntegerField(null=True, verbose_name="Expiry Days",
                                      help_text="Day count from valuation to expiry date for an option based on tenor.")

    rate = models.FloatField(null=True)  # FX forward rate
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    # Forward points (Fwd - Spot)
    fwd_points = models.FloatField(null=True)
    fwd_points_bid = models.FloatField(null=True)
    fwd_points_ask = models.FloatField(null=True)

    # Depo rates (base and quote currency)
    depo_base = models.FloatField(null=False)
    depo_quote = models.FloatField(null=False)

    class Meta:
        abstract = True
        unique_together = (("data_cut", "pair", "tenor"),)


class FxForward(AbstractFxForward):
    def days(self) -> int:
        """ Converts the tenor into days """
        return TenorConverter().get_days_from_tenor(tenor=self.tenor, fx_pair_name=self.pair.name)

    @staticmethod
    def create_forward_curve(data_cut: DataCut,
                             fx_pair: FxPair,
                             tenors: Sequence[str],
                             fwd_points: Sequence[float],
                             fwd_points_bid: Optional[Sequence[Optional[float]]] = None,
                             fwd_points_ask: Optional[Sequence[Optional[float]]] = None,
                             ):
        """
        Create a basic forward curve, all at once.

        Note - this function does not support all the functionality of creating a forward curve, it is primarily
        (currently) used to support testing, not to actually create forward curves from market data.
        """
        if len(tenors) != len(fwd_points):
            raise ValueError(f"length of tenors and rates must be the same in create_forward_curve")
        if fwd_points_bid is not None and len(fwd_points_bid) != len(tenors):
            raise ValueError(f"if bid_rates is not None, its length must match tenors")
        if fwd_points_ask is not None and len(fwd_points_ask) != len(tenors):
            raise ValueError(f"if ask_rates is not None, its length must match tenors")

        if fwd_points_bid is None:
            fwd_points_bid = [None for _ in tenors]
        if fwd_points_ask is None:
            fwd_points_ask = [None for _ in tenors]

        objects = []
        for tenor, mid, bid, ask in zip(tenors, fwd_points, fwd_points_bid, fwd_points_ask):
            obj = FxForward(date=data_cut.cut_time, data_cut=data_cut, pair=fx_pair, tenor=tenor,
                            fwd_points=mid, fwd_points_bid=bid, fwd_points_ask=ask,
                            depo_base=0, depo_quote=0)  # NOTE: Hard coded to zero.
            objects.append(obj)

        return FxForward.objects.bulk_create(objects)


class AbstractCorpayFxForward(Fx):
    """
    Fx Forward model, represents the Fx forward curve tenors per FX pair on a given date
    """
    tenor = models.CharField(max_length=4, null=False)
    tenor_days = models.IntegerField(null=False)

    rate = models.FloatField(null=True)  # FX forward rate
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    # Forward points (Fwd - Spot)
    fwd_points = models.FloatField(null=True)
    fwd_points_bid = models.FloatField(null=True)
    fwd_points_ask = models.FloatField(null=True)

    class Meta:
        abstract = True
        unique_together = (("date", "data_cut", "pair", "tenor"),)


class CorpayFxForward(AbstractCorpayFxForward):
    pass


class CorpayFxSpot(AbstractFxSpot):
    class Meta:
        unique_together = (("date", "data_cut", "pair"),)
