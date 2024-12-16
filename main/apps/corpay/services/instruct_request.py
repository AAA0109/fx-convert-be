from typing import Optional
from main.apps.corpay.models.spot.instruct_request import InstructRequest
from main.apps.corpay.services.api.dataclasses.spot import InstructDealOrder, InstructDealPayment, InstructDealSettlement
from main.apps.currency.models.currency import Currency
from main.apps.oems.models.quote import Quote


class InstructRequestService:
    instruct_request: dict
    quote: Optional[Quote]

    def __init__(self, instruct_request: dict, quote_id: Optional[int] = None) -> None:
        self.instruct_request = instruct_request
        try:
            self.quote = Quote.objects.get(pk=quote_id) if quote_id else None
        except Exception as e:
            raise Exception(f"Quote with id {quote_id} not found")

    def save_instruct_request(self) -> InstructRequest:
        orders = []
        for order in self.instruct_request.get('orders'):
            orders.append(
                InstructDealOrder(
                    orderId=order.get('order_id', ""),
                    amount=order['amount']
                )
            )
        payments = []
        for payment in self.instruct_request.get('payments'):
            payments.append(
                InstructDealPayment(
                    amount=payment['amount'],
                    beneficiaryId=payment['beneficiary_id'],
                    deliveryMethod=payment['delivery_method'],
                    currency=payment['currency'],
                    purposeOfPayment=payment['purpose_of_payment'],
                    paymentReference=payment['payment_reference']
                )
            )
        settlements = []
        for settlement in self.instruct_request.get('settlements'):
            settlements.append(
                InstructDealSettlement(
                    accountId=settlement['account_id'],
                    deliveryMethod=settlement['delivery_method'],
                    currency=settlement['currency'],
                    purpose=settlement['purpose']
                )
            )

        first_order: InstructDealOrder = orders[0]
        first_payment: InstructDealPayment = payments[0]
        from_settlement: InstructDealSettlement = settlements[0]
        to_settlement: InstructDealSettlement = settlements[1]

        from_currency = Currency.objects.get(mnemonic=from_settlement.currency)
        to_currency = Currency.objects.get(mnemonic=first_payment.currency)

        order_instruct_request = InstructRequest(
            amount = first_payment.amount,
            from_currency = from_currency,
            to_currency = to_currency,
            from_account_id = from_settlement.accountId,
            to_account_id = to_settlement.accountId,
            beneficiary_id = first_payment.beneficiaryId,
            order_id = first_order.orderId,
            purpose_of_payment = first_payment.purposeOfPayment,
            payment_reference = first_payment.paymentReference,
            from_purpose = from_settlement.purpose,
            to_purpose = to_settlement.purpose,
            delivery_method = first_payment.deliveryMethod,
            from_delivery_method = from_settlement.deliveryMethod,
            to_delivery_method = to_settlement.deliveryMethod,
            same_settlement_currency = from_settlement.currency == to_settlement.currency,
            quote = self.quote
        )
        order_instruct_request.save()

        return order_instruct_request
