from typing import Optional

from hdlib.Core.FxPairInterface import FxPairInterface
from main.apps.hedge.support.fx_fill_summary import FxFillSummary

import logging

logger = logging.getLogger(__name__)


class ReconciliationData:
    """
    An object that contains information related to the account reconciliation process. This can be used to verify the
    validity of the reconciliation, and is helpful during the reconciliation itself due its helper functions.
    """

    def __init__(self, fx_pair: FxPairInterface):
        # The Fx pair.
        self.fx_pair = fx_pair

        # The total change in the Fx pair that all the accounts together required.
        self.total_account_requested_change = 0.0

        # The sum of the absolute values of the requested per-account changes in position.
        self.absolute_sum_of_account_requests = 0.0

        # The Fx fill summary. If there was no order associated with this reconciliation, this will be None.
        self.fill_summary: Optional[FxFillSummary] = None

        # The initial amount of the Fx pair that the company had.
        self.initial_amount = 0.0

        # The final amount of the Fx pair that the company had.
        self.final_amount = 0.0

        # The total amount of Fx that all accounts want.
        self.desired_final_amount = 0.0

        # The amount that was filled either through liquidity pool, market, or both.
        self.filled_amount = 0.0

        # The sum of the absolute values of the desires per account final position.
        self.absolute_sum_of_desired_account_positions = 0.0

    @property
    def had_associated_order(self) -> bool:
        """
        Returns whether there was any order for the fx pair that occurred in the period of time that the
        reconciliation data is for.
        """
        return self.fill_summary is not None

    @property
    def excess_amount(self) -> float:
        """
        The difference between how much of the Fx pair that the accounts collectively desire, and the actual
        amount that the company has. Positive excess means there is more Fx than desired.
        """
        return self.final_amount - self.desired_final_amount

    @property
    def change_in_position(self) -> float:
        """ The change between the initial and final company positions. """
        return self.final_amount - self.initial_amount

    @property
    def market_filled_amount(self) -> float:
        """ How much of the Fx pair was filled by market orders. """
        return self.fill_summary.amount_filled if self.fill_summary else 0.0

    @property
    def commission(self) -> float:
        """ The amount of commission charged for orders. This will be zero if there were no orders. """
        return self.fill_summary.commission if self.fill_summary else 0.0

    @property
    def cntr_commission(self) -> float:
        """ The amount of commission charged for orders in the counter currency. """
        return self.fill_summary.cntr_commission if self.fill_summary else 0.0

    @property
    def average_price_from_trade(self) -> Optional[float]:
        """ Return the average price of the Fx pair during the trade if trading occurred, otherwise returns None. """
        return self.fill_summary.average_price if self.fill_summary else None

    @property
    def unexplained_change(self):
        """
        The change in the positions that cannot be accounted for by the orders that traded.

        Hopefully, this quantity will be very small. It may be non-zero though since Fx pairs are virtual, 'created'
        by pairing currency balances, and changes in balances due to roll costs (interest) or other fees may cause a
        change in the virtual FxPair holding.
        """
        return self.change_in_position - self.filled_amount

    @property
    def excess_change(self):
        """ The actual change in positions minus the total amount of change desired by the accounts. """
        return self.change_in_position - self.total_account_requested_change
