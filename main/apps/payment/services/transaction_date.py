from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.currency.models.fxpair import FxPair
from main.apps.payment.models.payment import Payment
from main.apps.oems.backend.calendar_utils import next_valid_settlement_day


class PaymentTransactionDateService:
    payment: Payment

    def __init__(self, payment:Payment) -> None:
        self.payment = payment

    def populate_transaction_dates(self) -> None:
        for cashflow in self.payment.related_cashflows:
            market = FxPair.get_pair_from_currency(
                base_currency=cashflow.sell_currency,
                quote_currency=cashflow.buy_currency
            )

            transaction_date = next_valid_settlement_day(mkt=market.market, day=cashflow.pay_date)
            cashflow.transaction_date = transaction_date
            cashflow.save()


class CashflowTransactionDateService:
    cashflow:SingleCashFlow

    def __init__(self, cashflow:SingleCashFlow) -> None:
        self.cashflow = cashflow

    def set_transaction_date(self) -> None:
        market = FxPair.get_pair_from_currency(
            base_currency=self.cashflow.sell_currency,
            quote_currency=self.cashflow.buy_currency
        )

        transaction_date = next_valid_settlement_day(
            mkt=market.market, day=self.cashflow.pay_date)

        self.cashflow.transaction_date = transaction_date
        self.cashflow.save()
