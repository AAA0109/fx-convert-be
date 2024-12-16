from django.db import models
from main.apps.currency.models import Currency, CurrencyId, CurrencyTypes
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.models.ir import Ir

from hdlib.DateTime.DayCounter import DayCounter, DayCountConvention, make_day_counter
from hdlib.DateTime.Date import Date

from typing import Iterable, Dict, Union, Sequence, Optional, List

# =====================================
# Type Definitions
# =====================================
CurveId = int  # id of an IrCurve
CurveName = str  # name of an IrCurve


class BasisConvention(models.IntegerChoices):
    """ Day Counting/Basis convention, used generally by interest rate computations """
    ACT_360 = 1  # Actual/360
    ACT_365 = 2  # Actual/365
    THIRTY_360 = 3  # 30/360
    THIRTY_365 = 4  # 30/365
    ACT_ACT = 5  # Actual/Actual

    def to_hdl(self) -> DayCountConvention:
        if self.value == 1:
            return DayCountConvention.ACT_360
        if self.value == 2:
            return DayCountConvention.ACT_365
        raise NotImplementedError("Need to map remaining types")


class IrCurve(models.Model):
    """
    Interest rate Curve. Each currency can have multiple curves, e.g. USD OIS, USD LIBOR
    """

    class Family(models.IntegerChoices):
        OIS = 1   # e.g., name = SOFR
        IBOR = 2  # e.g., name = 3M

    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    family = models.IntegerField(null=False, choices=Family.choices)
    name = models.CharField(max_length=255)  # e.g. SOFR, CORRA, AONIA, ESTER, SONIA, HONIA, TONAR, SORA, 3M
    long_name = models.CharField(max_length=255)  # e.g. Secured Overnight Financing Rate
    basis_convention = models.IntegerField(null=False, choices=BasisConvention.choices)

    class Meta:
        unique_together = (("currency", "name"),)

    def __str__(self):
        return self.currency.mnemonic + "_" + self.name

    @staticmethod
    def create_curve(currency: Currency,
                     family: Family,
                     name: str,
                     long_name: str,
                     basis_convention: BasisConvention) -> 'IrCurve':
        """ Convenience method for creating an IR curve. Returns the IR curve created. """
        return IrCurve.objects.create(currency=currency,
                                      family=family,
                                      name=name,
                                      long_name=long_name,
                                      basis_convention=basis_convention)

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_curves(family: int = Family.OIS) -> Sequence['IrCurve']:
        if family:
            return IrCurve.objects.filter(family=family)
        return IrCurve.objects.all()

    @staticmethod
    def get_ois_curve_id_by_currency(currencies: Optional[Iterable[Currency]] = None) -> Dict[str, int]:
        """ Get the ids (pk) of curves of single type (e.g. OIS) by currency """

        filters = {"family": IrCurve.Family.OIS}
        if currencies:
            filters["currency__in"] = currencies

        curves = IrCurve.objects.filter(**filters)
        return {irCurve.currency.mnemonic: irCurve.id for irCurve in curves}

    @staticmethod
    def get_ois_curve_id_for_currency(currency: CurrencyTypes) -> Optional[int]:
        """ Get the ois curve id for a specific currency """
        cny = Currency.get_currency(currency=currency)
        curves = IrCurve.get_ois_curve_id_by_currency(currencies=[cny])
        if not curves:
            return None

        return curves[cny.get_mnemonic()]

    def make_day_counter(self, include_end_date=False) -> DayCounter:
        """ Create a day counter for this IrCurve, based on its day count convention """
        return make_day_counter(convention=BasisConvention(self.basis_convention).to_hdl(),
                                include_end_date=include_end_date)


class Rate(Ir):
    """
    Abstract base class for an interest rate model, linked to an Ir curve
    """
    tenor = models.CharField(max_length=10, null=False)
    maturity = models.DateField()
    maturity_days = models.IntegerField(null=True)
    curve = models.ForeignKey(IrCurve, on_delete=models.CASCADE, null=True)

    rate = models.FloatField(null=False)
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    class Meta:
        unique_together = (("data_cut", "maturity", "curve"),)
        abstract = True

    def ttm(self, day_counter: DayCounter) -> float:
        """ Calculates the time to maturity for this discount factor """
        return day_counter.year_fraction_from_days(days=self.maturity_days)


class OISRate(Rate):
    """
    Represents the OIS curves for each currency, e.g. SOFR, EONIA, etc
    """
    fixing_rate = models.FloatField(null=True)

    # Basis spread data (basis to IBOR, if known)
    spread = models.FloatField(null=True)
    spread_index = models.CharField(max_length=10, null=True)  # e.g. "3M", for 3 month LIBOR-OIS spread


class IBORRate(Rate):
    """
    Represents the IBOR curves for each currency, e.g. LIBOR 6M
    """
    zero_rate = models.FloatField(null=True)  # zero bond equivalent rate

    # Instrument is the instrument type for this rate
    instrument = models.CharField(max_length=20, null=True)  # e.g. Cash, FRA, Swap, Futures


class IrDiscount(Ir):
    """
    Represents and interest rate discount, which together form a discount curve
    """
    maturity = models.DateField()
    maturity_days = models.IntegerField(null=True)
    curve = models.ForeignKey(IrCurve, on_delete=models.CASCADE, null=True)
    discount = models.FloatField(null=True)

    class Meta:
        unique_together = (("data_cut", "maturity", "curve"),)
        ordering = ['data_cut', 'curve', 'maturity']

    def ttm(self, day_counter: DayCounter) -> float:
        """ Calculates the time to maturity for this discount factor """
        return day_counter.year_fraction_from_days(days=self.maturity_days)

    @staticmethod
    def create_discount_curve(data_cut: DataCut,
                              maturities: Sequence[Date],
                              curve: IrCurve,
                              discounts: Sequence[float],
                              dc: Optional[DayCounter] = None) -> List['IrDiscount']:
        if len(maturities) != len(discounts):
            raise ValueError(f"dates and discounts need to be the same length")
        if len(maturities) == 0:
            return []

        ref_time = Date.from_datetime(data_cut.cut_time)
        currency = curve.currency

        discount_objects = []
        for maturity, df in zip(maturities, discounts):
            maturity_days = dc.days_between(ref_time, maturity) if dc else None

            ir_disc = IrDiscount(data_cut=data_cut,
                                 date=data_cut.cut_time,
                                 maturity=maturity,
                                 maturity_days=maturity_days,
                                 discount=df,
                                 curve=curve,
                                 currency=currency)
            discount_objects.append(ir_disc)

        return IrDiscount.objects.bulk_create(discount_objects)

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_most_recent_data_cut(
        ir_curves: Optional[Iterable[Union[CurveId, IrCurve]]] = None,
        ref_date: Optional[Date] = None) -> DataCut:
        """
        Get the most recent data cut that contains discounts
        :param ir_curves: iterable of curves (optional), if supplied restrict these curves, else all
        :param ref_date: Date (optional), if supplied, restrict to <= this date
        :return: DataCut, most recent one with discounts
        """
        filters = {}
        if ir_curves is not None:
            filters["curve__in"] = ir_curves
        if ref_date:
            filters["date__lte"] = ref_date

        return IrDiscount.objects.filter(**filters).order_by('-date')[0].data_cut

    @staticmethod
    def get_discounts_at_time(ir_curves: Iterable[Union[CurveId, IrCurve]],
                              time: Optional[Date] = None) -> Sequence['IrDiscount']:
        """
        Get Discounts for a collection of curves on a date. If a data cut is supplied, use it. If a date is supplied,
        use the lastest data cut less than or equal to that date
        """

        objs = IrDiscount.objects.filter(curve__in=ir_curves, data_cut__cut_time__lte=time)
        if not objs:
            return []
        data_cut = objs.latest("data_cut__cut_time").data_cut

        return IrDiscount.objects.filter(curve__in=ir_curves, data_cut=data_cut)

    @staticmethod
    def get_ois_discounts(currency: Union[Currency, CurrencyId],
                          data_cut: DataCut) -> Sequence['IrDiscount']:
        """ Get discounts for the ois curve for this family """
        curve = IrCurve.objects.filter(family=IrCurve.Family.OIS, currency=currency)
        if not curve:
            return ()
        return IrDiscount.objects.filter(curve=curve, data_cut=data_cut)
