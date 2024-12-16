from dataclasses import dataclass
from typing import Optional, Iterable, List

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class QuotePayment(JsonDictMixin):
    """The identifier of the beneficiary or the FXBalance to which the payment will be sent.
    For beneficiaries, use the 'persistentId' value which can be found by using the GET View Bene endpoint."""
    beneficiaryId: str
    """Method to use to send the payment = ['Wire', 'EFT', 'StoredValue']. 'StoredValue' = FXBalance"""
    paymentMethod: str
    """Payment amount."""
    amount: float
    """Indicates the base currency (of the currency pair),
    on which the rate calculation is based = ['payment', 'settlement']."""
    lockside: str
    """The three-letter ISO code for the payment currency."""
    paymentCurrency: str
    """The three-letter ISO code for the payment currency."""
    settlementCurrency: str
    """Settlement account identifier."""
    settlementAccountId: str
    """Method to use to settle the deal = ['Wire', 'EFT', 'StoredValue']. 'StoredValue' = FXBalance"""
    settlementMethod: str
    """Reference to be included with the payment. For example, purchase order number or invoice number."""
    paymentReference: str
    """The purpose of payment. Can be found by using GET Purpose of Payment.
    (https://apidocscrossborder.corpay.com/#39136fe2-5edc-4990-9010-ce4ea8354d9a)"""
    purposeOfPayment: str
    """Remitter ID"""
    remitterId: str = None
    """The date the payment will be delivered to the beneficiary, formatted as yyyy-mm-dd.
    Note: The maximum delivery date is three months from the entry date."""
    deliveryDate: str = None
    """The unique internal payment identifier that clients can assign to a payment transaction."""
    paymentId: str = None


@dataclass
class QuotePaymentsBody(JsonDictMixin):
    payments: List[QuotePayment]


@dataclass
class BookPaymentsParams(JsonDictMixin):
    """The 'quoteKey', and 'loginSessionId' params are contained in the URL,
    which is a unique feature of this workflow."""
    quoteKey: str
    loginSessionId: str


@dataclass
class BookPaymentsBody(JsonDictMixin):
    """Specifies whether to combine any associated fees into a single deduction. The default is 'false'."""
    combineSettlements: bool
