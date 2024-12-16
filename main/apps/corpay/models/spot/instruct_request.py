from django.db import models
from django.utils.translation import gettext_lazy as __

from main.apps.corpay.api.serializers.choices import DELIVERY_METHODS

from main.apps.corpay.models.spot import SpotDealRequest
from main.apps.corpay.services.api.dataclasses.spot import InstructDealBody, InstructDealOrder, InstructDealPayment, InstructDealSettlement
from main.apps.currency.models.currency import Currency
from main.apps.oems.models import Quote


class InstructRequest(SpotDealRequest):
    class SettlementPurposeOption(models.TextChoices):
        ALL = "All", __("All")
        ALLOCATION = "Allocation", __("Allocation")
        FEE = "Fee", __("Fee")
        SPOT = "Spot", __("Spot")
        SPOT_TRADE = "Spot_trade", __("Spot Trade")
        DRAWDOWN = "Drawdown", __("Drawdown")

    amount = models.FloatField()

    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, related_name='instruct_deal_request_to_currency')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, related_name='instruct_deal_request_from_currency')

    from_account_id = models.CharField(max_length=50, null=True, blank=True)
    to_account_id = models.CharField(max_length=50, null=True, blank=True)

    beneficiary_id = models.CharField(max_length=100, null=True, blank=True)
    order_id = models.CharField(max_length=50, null=True, blank=True)

    purpose_of_payment = models.CharField(max_length=255, null=True, blank=True)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)

    from_purpose = models.CharField(choices=SettlementPurposeOption.choices, null=True)
    to_purpose = models.CharField(choices=SettlementPurposeOption.choices, null=True)

    delivery_method = models.CharField(choices=DELIVERY_METHODS, null=True)
    from_delivery_method = models.CharField(choices=DELIVERY_METHODS, null=True)
    to_delivery_method = models.CharField(choices=DELIVERY_METHODS, null=True)

    same_settlement_currency = models.BooleanField(default=False)

    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, related_name='instruct_deal_request_quote')


    def to_instruct_deal_body(self, book_deal_response: dict) -> InstructDealBody:
        orders = []
        orders.append(
            InstructDealOrder(
                orderId=book_deal_response['orderNumber'],
                amount=self.amount
            )
        )

        payments = []

        payments.append(
            InstructDealPayment(
                amount=self.amount,
                beneficiaryId=self.beneficiary_id,
                deliveryMethod=self.delivery_method,
                currency=self.to_currency.mnemonic,
                purposeOfPayment=self.purpose_of_payment,
                paymentReference=self.payment_reference
            )
        )

        settlements_requests = {
            "from": {
                "account_id": self.from_account_id,
                "currency": self.from_currency.mnemonic,
                "purpose": self.from_purpose,
                "delivery_method": self.from_delivery_method
            },
            "to": {
                "account_id": self.to_account_id,
                "currency": self.to_currency.mnemonic if not self.same_settlement_currency else self.from_currency.mnemonic,
                "purpose": self.to_purpose,
                "delivery_method": self.to_delivery_method
            }
        }

        settlements = []
        for key in settlements_requests.keys():
            settlements_request = settlements_requests[key]
            settlements.append(
                InstructDealSettlement(
                    accountId=settlements_request.get('account_id'),
                    deliveryMethod=settlements_request.get('delivery_method'),
                    currency=settlements_request.get('currency'),
                    purpose=settlements_request.get('purpose')
                )
            )

        instruct_deal_body = InstructDealBody(
            orders=orders,
            payments=payments,
            settlements=settlements
        )

        return instruct_deal_body
