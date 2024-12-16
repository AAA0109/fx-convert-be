import logging

logger = logging.getLogger(__name__)


class FxFillSummary(object):
    """
    Object that summarizes the result of an OMS order.
    """

    def __init__(self,
                 amount_filled: float,
                 average_price: float,
                 commission: float = 0.,
                 cntr_commission: float = 0.):
        self.amount_filled = amount_filled
        self.average_price = average_price
        self.commission = commission
        self.cntr_commission = cntr_commission

    @staticmethod
    def make_empty() -> 'FxFillSummary':
        return FxFillSummary(amount_filled=0, commission=0, cntr_commission=0, average_price=0)
