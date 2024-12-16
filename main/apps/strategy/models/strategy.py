import logging
import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as __
from django_extensions.db.models import TimeStampedModel
from polymorphic.models import PolymorphicModel

from main.apps.account.models import Company
from main.apps.core.constants import LOCK_SIDE_HELP_TEXT
from main.apps.core.models.choices import LockSides
from main.apps.currency.models.currency import Currency

logger = logging.getLogger(__name__)


class HedgingStrategy(TimeStampedModel, PolymorphicModel):
    """
    Model for a hedging strategy.
    """

    class Meta:
        # the class should be abstract but Django-Polymorphic requires this to be False
        abstract = False
        unique_together = ('company', 'slug')

    strategy_id = models.UUIDField(default=uuid.uuid4, editable=False)

    slug = models.SlugField()

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="%(class)s_strategies", null=False)

    class Status(models.TextChoices):
        DRAFT = "draft", __("Draft")
        PENDING = "pending", __("Pending")
        APPROVED = "approved", __("Approved")
        LIVE = "live", __("Live")
        CANCELED = "canceled", __("Cancelled")

    status = models.CharField(max_length=24,
                              default=Status.DRAFT,
                              choices=Status.choices,
                              help_text="The status of the strategy")

    # ========================================================================================
    # Additional information
    # ========================================================================================
    name = models.CharField(max_length=255, null=True, help_text="A name for the strategy")
    description = models.TextField(null=True, help_text="A description of the strategy")

    # The buy currency of the strategy
    buy_currency = models.ForeignKey(Currency,
                                     on_delete=models.PROTECT,
                                     related_name='%(class)s_from_currency',
                                     null=True, blank=True,
                                     help_text="The from currency of the strategy")
    # The sell currency of the strategy
    sell_currency = models.ForeignKey(Currency,
                                      on_delete=models.PROTECT,
                                      related_name='%(class)s_to_currency',
                                      null=True, blank=True,
                                      help_text="The to currency of the strategy")

    # The side the currency is locked to
    lock_side = models.ForeignKey(Currency, on_delete=models.PROTECT,
                                  related_name='%(class)s_lock_side',
                                  null=True,
                                  blank=True,
                                  help_text=LOCK_SIDE_HELP_TEXT)


class SelfDirectedHedgingStrategy(HedgingStrategy):
    def save(self, **kwargs):
        if not self.id:
            self.slug = slugify(f"self-directed {self.from_currency} {self.to_currency} {self.lock_side}")
        super(SelfDirectedHedgingStrategy, self).save(**kwargs)


class AutopilotHedgingStrategy(HedgingStrategy):
    """
    Model for an autopilot hedging strategy.
    """

    class Meta:
        verbose_name = "Autopilot Hedging Strategy"
        verbose_name_plural = "Autopilot Hedging Strategies"

    # The amount of the strategy in its currency
    risk_reduction = models.FloatField(
        null=False,
        help_text="The ratio of the amount to be hedged (0.0 - 1,0)"
    )

    upper_target = models.FloatField(
        null=True,
        blank=True,
        help_text="The upper target for the strategy used to define a take-profit bound"
    )

    lower_target = models.FloatField(
        null=True,
        blank=True,
        help_text="The lower target for the strategy used to define a stop-loss bound"
    )

    def save(self, **kwargs):
        if not self.id:
            slug = f"autopilot {self.from_currency} {self.to_currency} {self.lock_side} {self.risk_reduction}"
            if self.upper_bound:
                slug += f" {self.upper_bound}"
            if self.lower_bound:
                slug += f" {self.lower_bound}"
            self.slug = slugify(slug)
        super(AutopilotHedgingStrategy, self).save(**kwargs)


class ZeroGravityHedgingStrategy(HedgingStrategy):
    """
    Model for a zero gravity hedging strategy.
    """

    class Meta:
        verbose_name = "Zero Gravity Hedging Strategy"
        verbose_name_plural = "Zero Gravity Hedging Strategies"

    margin_budget = models.FloatField(null=False,
                                      help_text="The margin budget for the strategy", default=2.e10)
    method = models.CharField(max_length=255,
                              null=False, help_text="The method used to calculate the strategy",
                              default="MIN_VAR")
    max_horizon_days = models.IntegerField(null=False,
                                           help_text="The maximum horizon days for the strategy",
                                           default=365 * 20)
    vol_target_reduction = models.FloatField(null=False,
                                             help_text="The vol target reduction for the strategy")
    var_95_exposure_ratio = models.FloatField(null=True,
                                              help_text="The VaR 95 exposure ratio for the strategy")
    var_95_exposure_window = models.IntegerField(null=True,
                                                 help_text="The VaR 95 exposure window for the strategy")


class ParachuteHedgingStrategy(HedgingStrategy):
    """
    The parachute hedge strategy
    """

    # TODO(Remove Parachute Data class)
    class Meta:
        verbose_name = "Parachute Hedging Strategy"
        verbose_name_plural = "Parachute Hedging Strategies"

    lower_limit = models.FloatField(null=False, help_text="The value that the account value should not drop below")

    # The probability of breaching the lower limit that, if greater than this, further positions should be taken.
    lower_p = models.FloatField(null=False, default=0.95, help_text="The probability of breaching the lower limit")

    # The probability that is adjusted to.
    upper_p = models.FloatField(null=False, default=0.99, help_text="The probability that is adjusted to")

    # If true, the first time the account value is in p-danger of breaching the lower limit, a full hedge will be put
    # on. If false, we just hedge back to upper-p, as usual.
    lock_lower_limit = models.BooleanField(null=False,
                                           default=False,
                                           help_text="If true, the first time the account value is in p-danger of "
                                                     "breaching the lower limit, a full hedge will be put on. "
                                                     "If false, we just hedge back to upper-p, as usual.")

    def save(self, **kwargs):
        if not self.id:
            slug = f"parachute {self.from_currency} {self.to_currency} {self.lock_side} {self.lower_limit} {self.lock_lower_limit}"
        super(ParachuteHedgingStrategy, self).save(**kwargs)
