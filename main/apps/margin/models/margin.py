from typing import Sequence, Tuple, Optional, Dict

from auditlog.registry import auditlog
from hdlib.DateTime import Date

from main.apps.broker.models import Broker
from main.apps.currency.models import FxPairTypes, FxPair
from main.apps.hedge.models import FxBrokerData
from main.apps.margin.services.broker_margin_service import MarginHealth
from main.apps.marketdata.models import DataCut
from main.apps.util import ActionStatus
from main.apps.account.models import Company
from main.apps.currency.models import Currency

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class MarginDetail(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    date = models.DateTimeField(auto_now_add=True)

    margin_requirement = models.FloatField(null=False, validators=[MinValueValidator(0.0)])

    excess_liquidity = models.FloatField(null=False)

    class Meta:
        unique_together = (("company", "date"),)

    @property
    def domestic(self) -> Currency:
        return self.company.currency

    def __str__(self):
        # display date, margin requirement, excess liquidity
        return f"[date: {self.date}, margin: {self.margin_requirement}, excess: {self.excess_liquidity}]"

    def get_margin_health(self) -> MarginHealth:
        return MarginHealth(excess_liquidity=self.excess_liquidity,
                            init_margin=self.margin_requirement, maint_margin=self.margin_requirement)

auditlog.register(MarginDetail)

class FxSpotMargin(FxBrokerData):
    """
    Model for FX spot margin rates for an FX holding at a particular broker.
    This corresponds to the univariate HAIRCUT rates charged by IB.
    """

    class Meta:
        verbose_name_plural = "FX Spot margins"
        unique_together = (("pair", "data_cut", "broker"),)

    # Initial Margin rate for the fx pair, between [0, 1]
    rate = models.FloatField(null=False, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    # Maintenance Margin Rate for the fx pair, between [0, 1]
    maintenance_rate = models.FloatField(null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    # NFA Margin Rate
    # The NFA is a self-regulatory organization for the U.S. futures industry that supervises Forex activity
    # in regulated Forex Dealer Members and Retail Foreign Exchange Dealers.
    nfa_rate = models.FloatField(null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_rates(date: Date,
                  broker: Broker,
                  fx_pairs: Optional[Sequence[FxPair]] = None,
                  initial_margin: bool = True) -> Tuple[Dict[FxPair, float], Dict[FxPair, DataCut]]:
        """
        Get the initial margin (IM) rates for a set of fx pairs (or maintenance margin, depending on value of flag)
        :param date: Date, The time at which the rates are requested.
        :param broker: Broker, identifies the broker
        :param fx_pairs: Optional[Sequence[FxPair]], Optionally get the rates only for select pairs.
        :param initial_margin: bool, if true return the initial margin, else the maintenance margin (unless its none,
            in which case the initial_margin=maintenance_margin)
        :return: pd.Series, rates per fx pair (index=fx.pair.name)
        """

        filters = {"broker": broker, "data_cut__cut_time__gt": date - 5, "data_cut__cut_time__lte": date}
        if fx_pairs:
            filters["pair__in"] = fx_pairs

        margin_rates = FxSpotMargin.objects.filter(**filters).prefetch_related().select_related()
        margins, cuts = {}, {}
        for margin in margin_rates:
            pair = margin.pair
            if pair not in margins or cuts[pair].cut_time < margin.data_time:
                if initial_margin or (not initial_margin and margin.maintenance_rate is None):
                    rate = margin.rate
                else:
                    rate = margin.maintenance_rate
                margins[pair] = rate
                cuts[pair] = margin.data_cut

        return margins, cuts

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def set_rate(fx_pair: FxPairTypes,
                 margin_rate: float,
                 data_cut: DataCut,
                 broker: Broker,
                 maintenance_rate: float = None,
                 nfa_rate: float = None,
                 update: bool = False) -> Tuple[ActionStatus, Optional['FxSpotMargin']]:
        fx_pair_ = FxPair.get_pair(fx_pair)
        if not fx_pair_:
            return ActionStatus.log_and_error(f"FX pair {fx_pair} does not exist."), None

        try:
            try:
                margin = FxSpotMargin.objects.get(pair=fx_pair_, data_cut=data_cut, broker=broker)
                if update:
                    margin.rate = margin
                    margin.maintenance_rate = maintenance_rate
                    margin.nfa_rate = nfa_rate
                    margin.save()
                    return ActionStatus.success(f"Updated margin rate"), margin

            except FxSpotMargin.DoesNotExist as e:
                margin = FxSpotMargin.objects.create(pair=fx_pair_,
                                                     date=data_cut.date,
                                                     rate=margin_rate,
                                                     data_cut=data_cut,
                                                     broker=broker,
                                                     maintenance_rate=maintenance_rate,
                                                     nfa_rate=nfa_rate)
                return ActionStatus.success(f"Added margin rate, cut {data_cut} for pair {fx_pair}"), margin
        except Exception as ex:
            return ActionStatus.log_and_error(f"Could not add margin haircut rate: {ex}"), None

        return ActionStatus.no_change(f"Margin hairtcut rate already exists and update was false"), margin

auditlog.register(FxSpotMargin)
