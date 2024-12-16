from dataclasses import dataclass
from typing import Optional, Iterable

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class SpotRateBody(JsonDictMixin):
    """The three-letter ISO code for the payment currency."""
    paymentCurrency: str
    """The three-letter ISO code for the settlement currency."""
    settlementCurrency: str
    """The amount on which to base the quote."""
    amount: float
    """Indicates which currency to lock when
    the rate calculation is performed = ['payment', 'settlement']."""
    lockSide: str


@dataclass
class InstructDealOrder(JsonDictMixin):
    """Number of the deal to which the payment and settlement instructions should be applied."""
    orderId: int
    """Payment amount"""
    amount: float


@dataclass
class InstructDealPayment(JsonDictMixin):
    """Payment amount"""
    amount: float
    """Identifier of the beneficiary/FXBalance to whom the payment will be sent.
    Value can be either 'clientIntegrationId' or 'id'"""
    beneficiaryId: str
    """Method to use to send the payment = ['W', 'E', 'C'].
    'W' = Wire
    'E' = iACH
    'C' = FXBalance"""
    deliveryMethod: str
    """Three-letter ISO code for the payment currency."""
    currency: str
    """The purpose of payment.
    Can be found here: GET Purpose of Payment
    (https://apidocscrossborder.corpay.com/#39136fe2-5edc-4990-9010-ce4ea8354d9a)"""
    purposeOfPayment: str
    """Reference to be included with the payment, for example, purchase order number or invoice number."""
    paymentReference: Optional[str] = None
    """Identifier of the remitter on whose behalf the payment is being made."""
    remitterId: Optional[str] = None


@dataclass
class InstructDealSettlement(JsonDictMixin):
    """Settlement account identifier."""
    accountId: str
    """Method to use to settle the deal = ['W', 'E', 'C'].
    'W' = Wire
    'E' = iACH
    'C' = FXBalance"""
    deliveryMethod: str
    """Three-letter ISO code for the settlement account currency."""
    currency: str
    """The reason for the settlement =
    ['All', 'Allocation', 'Fee', 'Spot', 'SpotTrade', 'Drawdown']."""
    purpose: str


@dataclass
class InstructDealBody(JsonDictMixin):
    orders: Iterable[InstructDealOrder]
    payments: Iterable[InstructDealPayment]
    settlements: Iterable[InstructDealSettlement]


@dataclass
class PurposeOfPaymentParams(JsonDictMixin):
    """Country ISO Code"""
    countryISO: str
    """Currency ISO Code"""
    curr: str
    """Payment method = [W, E]"""
    method: str
