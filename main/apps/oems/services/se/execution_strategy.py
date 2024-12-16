from datetime import date, datetime
from typing import Optional
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.api.dataclasses.best_execution import FxSpotInfo
from main.apps.oems.backend.calendar_utils import get_fx_spot_info
from main.apps.oems.services.currency_execution import CompanyCnyExecutionProvider


class CashflowExecutionStrategy:
    cashflow:SingleCashFlow

    def __init__(self, cashflow:SingleCashFlow) -> None:
        self.cashflow = cashflow

    def is_scheduled_spot(self, spot_date:Optional[date] = None) -> bool:
        pair = FxPair.get_pair_from_currency(
            base_currency=self.cashflow.sell_currency,
            quote_currency=self.cashflow.buy_currency
        )

        cny_exec_svc = CompanyCnyExecutionProvider(company=self.cashflow.company, fx_pair=pair)
        is_ndf, fwd_rfq_type = cny_exec_svc.is_ndf()

        if is_ndf:
            if spot_date is None:
                now = datetime.utcnow()
                fx_spot_info = get_fx_spot_info(mkt=pair.market, dt=now)
                fx_spot_info = FxSpotInfo(**fx_spot_info)
                spot_date = fx_spot_info.spot_value_date

            if self.cashflow.pay_date.date() > spot_date:
                return True

        return False
