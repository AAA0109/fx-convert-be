from dataclasses import dataclass
from typing import Optional, Iterable

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class RequestForwardQuoteBody(JsonDictMixin):
    """
    Request body class for POST /api/{clientCode}/0/quotes/forward
    """

    """The amount of currency locked into the forward agreement."""
    amount: float
    """Three-letter ISO code for the currency being bought"""
    buyCurrency: str
    """Contract type is determined according to business needs.
    Possible values = ['C', closed contract; 'O', open contract]."""
    forwardType: str
    """Indicates which currency should be locked
    when the rate calculation is performed = ['payment', 'settlement']"""
    lockSide: str
    """The date of forward maturity, formatted as yyyy-mm-dd."""
    maturityDate: str
    """Three-letter ISO code for the settlement-side currency."""
    sellCurrency: str
    """required if 'forwardType': 'O'
    Applies only to Open Forwards., formatted as yyyy-mm-dd."""
    OpenDateFrom: Optional[str] = None


@dataclass
class CompleteOrderBody(JsonDictMixin):
    """The settlement account."""
    settlementAccount: str
    """Any comments or reference information related to the forward."""
    forwardReference: Optional[str] = None


@dataclass
class DrawdownOrder(JsonDictMixin):
    """The forward number (alphanumeric)."""
    orderId: str

    """The drawdown amount."""
    amount: float


@dataclass
class DrawdownPaymentFee(JsonDictMixin):
    """The fee amount, paid in the 'currency' field.
    If you do not know the fee amount, enter '0' and
    set 'expectation' to 'AnyFee'."""
    amount: float

    """If you know the exact amount of the fee, set to 'ExactFee'
    and enter the fee amount in the 'amount' field.

    If you do not know the fee amount, set to 'AnyFee'."""
    expectataion: Optional[str] = None

    """Three-letter ISO code of the fee currency."""
    currency: Optional[str] = None


@dataclass
class DrawdownPayment(JsonDictMixin):
    """Identifier of the beneficiary (or FXBalance) to whom the payment will be sent.
    Value can be either 'clientIntegrationId' or 'id' (which is returned by GET View Bene
    <https://apidocscrossborder.corpay.com/#834bd180-758c-45c2-80a0-073296e83946>)."""
    beneficiaryId: str

    """Method to use to instruct the drawdown = ['W', 'E', 'C'].
    'W' = Wire
    'E' = iACH
    'C' = FXBalance"""
    deliveryMethod: str

    """The buy amount."""
    amount: float

    """Three-letter ISO code for the buy currency."""
    currency: str

    """The purpose of payment. Can be found here: GET Purpose of Payment
    <https://apidocscrossborder.corpay.com/#39136fe2-5edc-4990-9010-ce4ea8354d9a>"""
    purposeOfPayment: str

    """Fee for payment"""
    fee: DrawdownPaymentFee

    """Reference to be included with the payment, for example, purchase order number or invoice number."""
    paymentReference: Optional[str] = None

    """Identifier of the remitter on whose behalf the payment is being made."""
    remitterId: Optional[str] = None


@dataclass
class DrawdownSettlement(JsonDictMixin):
    """The account identifier of the settlement account template."""
    accountId: str

    """Method to use to settle the deal = ['W', 'E', 'C'].
    'W' = Wire
    'E' = iACH
    'C' = FXBalance"""
    deliveryMethod: str

    """Three-letter ISO code for the settlement account currency."""
    currency: str

    """Purpose should be 'All' or 'Drawdown'."""
    purpose: str


@dataclass
class DrawdownBody(JsonDictMixin):
    """
    Request body class for POST /api/{clientCode}/0/book-drawdown
    """
    orders: Iterable[DrawdownOrder]
    payments: Iterable[DrawdownPayment]
    settlements: Iterable[DrawdownSettlement]
