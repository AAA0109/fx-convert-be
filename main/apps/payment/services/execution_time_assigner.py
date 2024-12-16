import logging
from typing import List, Optional, Union
from datetime import date

from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.backend.calendar_utils import get_spot_dt
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.payment.models import Payment

logger = logging.getLogger(__name__)


class PaymentExecutionTimeAssigner:
    payments:List[Payment]
    payment:Payment

    def __init__(self, payment:Optional[Payment] = None, payments:Optional[List[Payment]]=None) -> None:
        self.payments = payments
        self.payment = payment

    def set_execution_time(self, payment:Payment) -> Payment:
        pair = FxPair.get_pair_from_currency(
                base_currency=payment.cashflow_generator.sell_currency,
                quote_currency=payment.cashflow_generator.buy_currency
            )
        try:
            ref_date = payment.cashflow_generator.value_date
            execution_timing = self.determine_execution_time(market=pair.market, value_date=ref_date)
            payment.execution_timing = execution_timing
        except ValueError as e:
            logging.error(e, exc_info=True)
        return payment

    def determine_execution_time(self, market:str, value_date:date) -> str:
        spot_date, valid_days, spot_days = get_spot_dt(mkt=market)
        if value_date > spot_date:
            return Payment.ExecutionTiming.SCHEDULED

        best_ex_status = get_best_execution_status(market_name=market)
        if best_ex_status.get('recommend', False):
            return Payment.ExecutionTiming.IMMEDIATE
        return Payment.ExecutionTiming.STRATEGIC_EXECUTION

    def assign_execution_time(self) -> Optional[Union[Payment, List[Payment]]]:
        if self.payment:
            self.payment = self.set_execution_time(payment=self.payment)
            self.payment.save()
            return self.payment
        elif self.payments:
            for payment in self.payments:
                payment = self.set_execution_time(payment=payment)
            Payment.objects.bulk_update(self.payments, ['execution_timing'])
            return self.payments
        return None
