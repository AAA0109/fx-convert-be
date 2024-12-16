import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Iterable

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class BeneficiaryRulesQueryParams(JsonDictMixin):
    """
    Query params class for GET /api/{clientCode}/0/template-guide
    """

    """ISO2 country code"""
    destinationCountry: str
    """ISO2 country code"""
    bankCountry: str
    """ISO3 currency code"""
    bankCurrency: str
    """'business' or 'individual'"""
    classification: str
    """'W'- Wire, 'E' - iACH"""
    paymentMethods: str
    """Tempalte Type"""
    templateType: str = 'Bene'


@dataclass
class BeneficiaryRequestBody(JsonDictMixin):
    """
    Request body for POST /api/{clientCode}/0/templates/{clientIntegrationId}
    """

    """Full name of the account holder"""
    accountHolderName: str

    """Two-letter ISO code for the country where the beneficiary's bank is located."""
    destinationCountry: str

    """Three-letter ISO code for the bank account currency."""
    bankCurrency: str

    """Beneficiary classification = 'Individual' or 'Business'.
    Most of the other values shown in GET Beneficiary Rules."""
    classification: str

    """Methods of payment that can be used for this beneficiary = ['W' or 'E']"""
    paymentMethods: List[str]

    """Method of payment preferred by this beneficiary."""
    preferredMethod: str

    """Bank account number."""
    accountNumber: str

    """Bank routing code - used to identify a specific financial institution.
    In some countries, the routing code is known by another name, such as ABA Number, Transit Number, Sort Code, BSB Number,
    IFSC Code, or Branch Code."""
    routingCode: str

    """The account holder's two-letter ISO country code."""
    accountHolderCountry: str

    """The account holder's province or state."""
    accountHolderRegion: str

    """First line of the account holder's address."""
    accountHolderAddress1: str

    """The account holder's city."""
    accountHolderCity: str

    """The account holder's postal or zip code."""
    accountHolderPostal: str

    """Name of the financial institution."""
    bankName: str

    """The bank's two-letter ISO country code."""
    bankCountry: str

    """The bank's city."""
    bankCity: str

    """First line of the bank's address."""
    bankAddressLine1: str

    """The client-assigned template identifier. This value should match the 'clientIntegrationId' in the URL.
    The value in this field is returned in the 'beneIdentifier' field when you run GET View Bene."""
    templateIdentifier: Optional[str] = None

    """Bank account number."""
    localAccountNumber: Optional[str] = None

    """Bank routing code."""
    localRoutingCode: Optional[str] = None

    """Second line of the account holder's address."""
    accountHolderAddress2: Optional[str] = None

    """The account holder's phone number."""
    accountHolderPhoneNumber: Optional[str] = None

    """Email address."""
    accountHolderEmail: Optional[str] = None

    """Specifies whether to send an email alert to the beneficiary
    whenever a payment is released = ['true', 'false']."""
    sendPayTracker: Optional[bool] = None

    """The bank's IBAN number. The IBAN accurately identifies the correct bank and bank account."""
    iban: Optional[str] = None

    """The unique identifier for the bank or financial institution."""
    swiftBicCode: Optional[str] = None

    """The bank's province or state."""
    bankRegion: Optional[str] = None

    """Second line of the bank's address."""
    bankAddressLine2: Optional[str] = None

    """The bank's postal or zip code."""
    bankPostal: Optional[str] = None

    """Default payment reference that will be used if a reference is not provided on a payment.
    The payment reference is transmitted with the payment, subject to banking constraints."""
    paymentReference: Optional[str] = None

    """Internal email addresses to notify when a payment is made to this beneficiary."""
    internalPaymentAlert: Optional[str] = None

    """External email addresses to notify when a payment is made to this beneficiary."""
    externalPaymentAlert: Optional[str] = None

    """The fields and corresponding values needed to satisfy regulatory requirements for the destination country."""
    regulatory: Optional[List[dict]] = None

    def __post_init__(self):
        self.validate_max_length("accountHolderName", self.accountHolderName, 100)
        self.validate_account_holder_name("accountHolderName", self.accountHolderName)
        self.validate_max_length("templateIdentifier", self.templateIdentifier, 50)
        self.validate_max_length("accountHolderRegion", self.accountHolderRegion, 30)
        self.validate_max_length("accountHolderAddress1", self.accountHolderAddress1, 1000)
        self.validate_max_length("accountHolderAddress2", self.accountHolderAddress2, 100)
        self.validate_max_length("accountHolderCity", self.accountHolderCity, 100)
        self.validate_max_length("accountHolderPostal", self.accountHolderPostal, 50)
        self.validate_max_length("bankName", self.bankName, 250)
        self.validate_max_length("bankRegion", self.bankRegion, 100)
        self.validate_max_length("bankCity", self.bankCity, 100)
        self.validate_max_length("bankAddressLine1", self.bankAddressLine1, 100)
        self.validate_max_length("bankAddressLine2", self.bankAddressLine2, 100)
        self.validate_max_length("bankPostal", self.bankPostal, 50)

    def validate_max_length(self, field_name: str, field_value: str, max_length: int):
        if field_value is not None and len(field_value) > max_length:
            raise ValueError(f"{field_name} exceeds the maximum length of {max_length} characters.")

    @staticmethod
    def validate_account_holder_name(field_name: str, field_value: str):
        if not re.match("^[a-zA-ZÀ-ÿ0-9.,&\\- ]*$", field_value):
            raise ValueError(
                f"{field_name} can only contain letters, numbers, spaces, periods, commas, ampersands, and dashes.")


@dataclass
class BeneficiaryListQ(JsonDictMixin):
    """The ISO-4217 Currency Code"""
    Curr: Optional[str] = None
    """The ISO2 Country Code"""
    PayeeCountryISO: Optional[str] = None
    """The method of payment = ['W' or 'E'] 'W' = Wire 'E' = iACH"""
    Methods: Optional[str] = None
    """The status of the benficiary template - 'Active', or 'Inactive' = ['A' or 'I']"""
    Status: Optional[str] = None

    def dict(self):
        output = ""
        for k, v in asdict(self).items():
            if v is not None:
                output += f"{k}:{v} "
        return output


@dataclass
class BeneficiaryListQueryParams(JsonDictMixin):
    """Page number"""
    skip: Optional[int] = 0
    """Number of records to per page"""
    take: Optional[int] = 100
    """Query Params for Beneficiary GET /api/{clientCode}/0/benes?q={query}"""
    q: Optional[BeneficiaryListQ] = None


@dataclass
class BankSearchParams(JsonDictMixin):
    """Query params for Bank Search GET /api/banks"""

    """country ISO2"""
    country: str

    """search string"""
    query: str

    """number of objects to skip; optional"""
    skip: int = None

    """number of objects to retrieve; optional"""
    take: int = None


@dataclass
class IbanValidationRequestBody(JsonDictMixin):
    iban: str
