from typing import Tuple, Optional, Iterable
import logging

from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company
from main.apps.currency.models import FxPair
from main.apps.hedge.support.fx_fill_summary import FxFillSummary
from main.apps.hedge.support.reconciliation_data import ReconciliationData

logger = logging.getLogger(__name__)


class ReconciliationRecord(models.Model):
    """
    A model that contains information about how reconciliations happened for companies.

    This should give us some idea of how our positions drift over time due to costs and fees, and allows us to
    better audit the account positions.
    """

    class Meta:
        unique_together = (("reference_time", "fx_pair", "company", "is_live"),)

    # Reference time, the time at which the reconciliation occurred.
    reference_time = models.DateTimeField(null=False)

    # The company that this reconciliation was done for.
    company = models.ForeignKey(Company, null=False, on_delete=models.CASCADE)

    # Whether this entry is for live positions. If false, it is for DEMO positions.
    is_live = models.BooleanField(null=False, default=True)

    # The Fx pair this reconciliation data is for.
    fx_pair = models.ForeignKey(FxPair, null=False, on_delete=models.CASCADE)

    # The total change in the Fx pair that all the accounts together required.
    total_account_requested_change = models.FloatField(null=False, default=0.0)

    # The sum of the absolute values of the requested per-account changes in position.
    absolute_sum_of_account_requests = models.FloatField(null=False, default=0.0)

    # The sum of the absolute values of the desires per account final position.
    absolute_sum_of_desired_account_positions = models.FloatField(null=False, default=0.0)

    # The initial amount of the Fx pair that the company had.
    initial_amount = models.FloatField(null=False, default=0.0)

    # The final amount of the Fx pair that the company had.
    final_amount = models.FloatField(null=False, default=0.0)

    # ==================================
    #  Data from the FxFillSummary.
    # ==================================

    # The Fx fill summary. If there was no order associated with this reconciliation, this will be None.

    # The amount of this Fx pair that was purchased between reconciliations. If none, the field is null.
    amount_filled = models.FloatField(null=True, default=None)

    # The commission for purchase of this Fx pair that occurred between reconciliations. If none, the field is null.
    commission = models.FloatField(null=True, default=None)

    # The commission in cntr currency convention for purchase of this Fx pair that occurred between reconciliations.
    # If none, the field is null.
    cntr_commission = models.FloatField(null=True, default=None)

    # The average price at which this Fx pair was purchased for any purchase that occurred between reconciliations.
    # If none, the field is null.
    average_price = models.FloatField(null=True, default=None)

    # ==================================
    #  Convenience methods.
    # ==================================

    @property
    def had_fx_fill_summary(self):
        """ Check if the entry had a fill. """
        return self.amount_filled is not None

    def make_fx_fill_summary(self) -> Optional[FxFillSummary]:
        """
        Make the equivalent FxFillSummary as that which is stored in the entry.
        """
        if not self.had_fx_fill_summary:
            return None
        return FxFillSummary(amount_filled=self.amount_filled,
                             commission=self.commission,
                             cntr_commission=self.cntr_commission,
                             average_price=self.average_price)

    def make_reconciliation_data(self) -> Tuple[Date, Company, ReconciliationData]:
        """
        Turn the model entry into a Date, Company, and the rest of the data as a ReconciliationData structure.
        """
        data = ReconciliationData(fx_pair=self.fx_pair)
        data.total_account_requested_change = self.total_account_requested_change
        data.absolute_sum_of_account_requests = self.absolute_sum_of_account_requests
        data.absolute_sum_of_desired_account_positions = self.absolute_sum_of_desired_account_positions
        data.initial_amount = self.initial_amount
        data.final_amount = self.final_amount
        data.fill_summary = self.make_fx_fill_summary()

        return Date.from_datetime(self.reference_time), self.company, data

    @staticmethod
    def create_from_reconciliation_data(time: Date,
                                        company: Company,
                                        is_live: bool,
                                        reconciliation_data: Iterable[ReconciliationData]):
        """
        Create a reconciliation record entry directly from a reconciliation data and some addition data.
        """
        for data in reconciliation_data:
            obj = ReconciliationRecord.objects.create(
                reference_time=time,
                company=company,
                is_live=is_live,
                fx_pair=data.fx_pair,
                total_account_requested_change=data.total_account_requested_change,
                absolute_sum_of_account_requests=data.absolute_sum_of_account_requests,
                absolute_sum_of_desired_account_positions=data.absolute_sum_of_desired_account_positions,
                initial_amount=data.initial_amount,
                final_amount=data.final_amount
            )
            if data.fill_summary is not None:
                obj.amount_filled = data.fill_summary.amount_filled
                obj.commission = data.fill_summary.commission
                obj.cntr_commission = data.fill_summary.cntr_commission
                obj.average_price = data.fill_summary.average_price
                obj.save()

    @staticmethod
    def get_last_reconciliation_time(company: Company, time: Date, inclusive: bool = False) -> Optional[Date]:
        """
        Get the latest reconciliation record that exists for the company either strictly before or inclusively before
        the specified time.
        """
        filters = {"company": company}
        if inclusive:
            filters["reference_time__lte"] = time
        else:
            filters["reference_time__lt"] = time
        q = ReconciliationRecord.objects.filter(**filters).order_by("-reference_time")
        if q:
            return Date.from_datetime(q.first().reference_time)
        return None
