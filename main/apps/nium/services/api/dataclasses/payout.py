from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable, Literal, Optional

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


class PurposeCode(Enum):
    TRANSFER_TO_OWN_ACCOUNT = "IR001"
    FAMILY_MAINTENANCE = "IR002"
    EDUCATION_RELATED_STUDENT_EXPENSES = "IR003"
    MEDICAL_TREATMENT = "IR004"
    HOTEL_ACCOMMODATION = "IR005"
    TRAVEL = "IR006"
    UTILITY_BILLS = "IR007"
    REPAYMENT_OF_LOANS = "IR008"
    TAX_PAYMENT = "IR009"
    PURCHASE_OF_RESIDENTIAL_PROPERTY = "IR010"
    PAYMENT_OF_PROPERTY_RENTAL = "IR011"
    INSURANCE_PREMIUM = "IR012"
    PRODUCT_INDEMNITY_INSURANCE = "IR013"
    INSURANCE_CLAIMS_PAYMENT = "IR014"
    MUTUAL_FUND_INVESTMENT = "IR015"
    INVESTMENT_IN_SHARES = "IR016"
    DONATIONS = "IR017"
    INFORMATION_SERVICE_CHARGES = "IR01801"
    ADVERTISING_PUBLIC_RELATIONS_EXPENSES = "IR01802"
    ROYALTY_FEES_TRADEMARK_FEES_PATENT_FEES_COPYRIGHT_FEES = "IR01803"
    FEES_FOR_BROKERS_FRONT_END_FEE_COMMITMENT_FEE_GUARANTEE_FEE_CUSTODIAN_FEE = "IR01804"
    FEES_FOR_ADVISORS_TECHNICAL_ASSISTANCE_ACADEMIC_KNOWLEDGE_SPECIALISTS = "IR01805"
    REPRESENTATIVE_OFFICE_EXPENSES = "IR01806"
    CONSTRUCTION_COSTS_EXPENSES = "IR01807"
    TRANSPORTATION_FEES_FOR_GOODS = "IR01808"
    PAYMENT_FOR_EXPORTED_GOODS = "IR01809"
    DELIVERY_FEES_FOR_GOODS = "IR01810"
    GENERAL_GOODS_TRADES_OFFLINE_TRADE = "IR01811"


class SourceOfFunds(Enum):
    SALARY = "Salary"
    PERSONAL_SAVINGS = "Personal Savings"
    PERSONAL_WEALTH = "Personal Wealth"
    RETIREMENT_FUNDS = "Retirement Funds"
    BUSINESS_OWNER_SHAREHOLDER = "Business Owner/Shareholder"
    LOAN_FACILITY = "Loan Facility"
    PERSONAL_ACCOUNT = "Personal Account"
    CORPORATE_ACCOUNT = "Corporate Account"


@dataclass
class Tag(JsonDictMixin):
    """
    This field accepts the Client's custom key of the tag.
    The maximum key length limit is 128 characters.
    """
    key: str

    """
    This field accepts the Client's custom value of the tag.
    The maximum value length limit is 256 characters.
    """
    value: str


@dataclass
class AdditionalFees(JsonDictMixin):
    """
    This field accepts the fee type as FIXED (flat) or PERCENTAGE
    """
    feeType: Literal['FIXED', 'PERCENTAGE']

    """
    This field accepts the client's fee value to be added on existing fee value
    """
    feeValue: float

    """
    This field accepts the client's additional fx markup rate to be added on existing fx markup
    """
    fxMarkup: float


@dataclass
class BeneficiaryDetail(JsonDictMixin):
    """
    required
    This is an unique beneficiary ID which depends upon the destination currency and payout method.
    The beneficiary Id and payout ID can be obtained using
    """
    id: str


@dataclass
class DeviceDetail(JsonDictMixin):
    """
    This field accepts the country IP for the device by the customer for initiating the request.
    """
    countryIP: str

    """
    This field accepts the device information used by the customer for initiating the request.
    """
    deviceInfo: str

    """
    This field accepts the IP address of the device used by the customer for initiating the request.
    """
    ipAddress: str

    """
    This field accepts the session Id for the session of the customer for initiating the request.
    """
    sessionId: str


@dataclass
class Payout(JsonDictMixin):
    """"
    The audit Id must be taken from Exchange Rate Lock and Hold API
    [https://docs.nium.com/apis/reference/exchangeratelockandhold].
    """
    audit_id: int

    """
    This field accepts the destination amount for remittance.
    Either the source or the destination amount is mandatory.
    Allowed decimal limit is 2.
    """
    destination_amount: float

    """
    This field indicates if compliance checks are to be done at the time of payout creation.
    This field is applicable only for scheduled and Post-Funded payouts.
    """
    preScreening: bool

    """
    This field accepts scheduled payout date in yyyy-MM-dd format
    """
    scheduledPayoutDate: date

    """
    This field should denote the date of providing of service/export in yyyy-MM-dd format
    """
    serviceTime: date

    """
    This field accepts the source amount for remittance.
    Either the source or the destination amount is mandatory.
    """
    source_amount: float

    """
    This field accepts the source currency for remittance.
    """
    source_currency: str

    """
    This field accepts the swift fee type and defines who will bear the SWIFT charges for the given transaction.
    Clients can send any of the below values basis which, they will be charged for the SWIFT transaction.
    In case this field is absent SHA will be applied by default.

    OUR - SWIFT charges borne by the customer
    SHA - SWIFT charges shared by the customer and beneficiary

    Note: Clients should make sure that fee template is configured for each of the swift fee type.
    To know if the template is configured, clients should call Fee Details API
    """
    swiftFeeType: Literal['OUR', 'SHA']

    """
    This field should denote the invoice number relevant to the transaction
    """
    tradeOrderID: str


@dataclass
class Remitter(JsonDictMixin):
    """
    This field accepts the Remitter's account type as INDIVIDUAL or CORPORATE
    """
    accountType: Optional[Literal['INDIVIDUAL', 'CORPORATE']] = None

    """
    This field accepts address for Remitter's place of residence.
    """
    address: Optional[str] = None

    """
    This field accepts the account number of the Remitter.
    """
    bankAccountNumber: Optional[str] = None

    """
    This field accepts the city for Remitter's place of residence.
    """
    city: Optional[str] = None

    """
    This field accepts the Remitter's contact number.
    """
    contactNumber: Optional[str] = None

    """
    This field accepts the country of residence for the remitter.
    """
    countryCode: Optional[str] = None

    """
    This field accepts Remitter's birth date.
    """
    dob: Optional[str] = None

    """
    The expiration date of the identification document.
    """
    idExpiryDate: Optional[str] = None

    """
    The date the identification document was issued.
    """
    idIssueDate: Optional[str] = None

    """
    ID number of the selected identificationType.
    """
    identificationNumber: Optional[str] = None

    """
    This field accepts the ID document type of the remitter e.g. Passport, National_ID etc..
    """
    identificationType: Optional[str] = None

    """
    This field accepts industry type associated with the remitter.
    """
    industryType: Optional[str] = None

    """
    This field accepts the name of the remitter.
    """
    name: Optional[str] = None

    """
    This field accepts Remitter's nationality.
    """
    nationality: Optional[str] = None

    """
    The city of the financial institution where the request was initiated.
    """
    originatingFICity: Optional[str] = None

    """
    The country of the financial institution where the request was initiated.
    """
    originatingFICountry: Optional[str] = None

    """
    The name of the financial institution where the request was initiated.
    Typically applicable for requests that don't originate from a financial
    institution that is a direct customer of Nium.
    """
    originatingFIName: Optional[str] = None

    """
    This field accepts Remitter's place of birth.
    """
    placeOfBirth: Optional[str] = None

    """
    This field accepts the postcode for Remitter's place of residence.
    """
    postcode: Optional[str] = None

    """
    This field accepts the state for Remitter's place of residence.
    """
    state: Optional[str] = None


@dataclass
class TransferMoneyPayload(JsonDictMixin):
    """
    required
    This object will accept the beneficiary details.
    """
    beneficiary: BeneficiaryDetail

    """
    This field applies only to licensed financial institutions.
    Boolean value 'false' indicates an on-behalf payout request or 'true' indicates a payout executed by the Financial Institution itself.
    If the field is absent from the request, the default flag is set to 'false'.
    A valid remitter object is required to be passed for on-behalf payout.
    """
    ownPayment: bool

    """
    required
    This object accepts the payout details.
    """
    payout: Payout

    """
    required
    This field accepts the purpose code for the payment.
    Refer to the Glossary of Purpose Codes to identify the correct value to be provided.
    If purpose code value is not passed then the default value will be IR01802 (Advertising & Public relations-related expenses).
    """
    purposeCode: PurposeCode

    """
    required
    This field accepts the source of funds
    """
    sourceOfFunds: SourceOfFunds

    """
    This is an array which accepts custom tags & values.
    Maximum 15 key-value pairs can be sent in tags.
    """
    tags: Optional[Iterable[Tag]] = None

    """
    This object accepts the Client's additional fees
    """
    additionalFees: Optional[AdditionalFees] = None

    """
    This field accepts the authentication code generated as part of SCA (Strong Customer Authentication).
    Note: Either exemption code or authentication is expected if the program's regulatory region is UK or EU.
    This field does not accept a value for any other region.
    """
    authenticationCode: Optional[str] = None

    """
    This field is used to add any customer comments.
    Maximum character limit is 512.
    Note: Special characters are not allowed in this field.
    """
    customerComments: Optional[str] = None

    """
    This object accepts the device and IP details for the transaction.
    """
    deviceDetails: Optional[DeviceDetail] = None

    """
    This field accepts the reason code for the exemption provided as part of SCA (Strong Customer Authentication).
    This must be 2 character string and the valid values are as following:
        01 - Trusted Beneficiary
        03 - Recurring Transactions
        04 - Payment to Self
    Note: Exemption code is expected if authenticationCode is not provided and regulatory region is UK or EU.
    """
    exemptionCode: Optional[Literal[
        '01 - Trusted Beneficiary',
        '03 - Recurring Transactions',
        '04 - Payment to Self'
    ]] = None

    """
    This object accepts the Remitter details while doing on-behalf payouts.
    This object applies only to licensed financial institutions.
    """
    remitter: Optional[Remitter] = None


@dataclass
class TransferMoneyResponse(JsonDictMixin):
    """
    This field is estimated delivery time of transaction.
    """
    estimatedDeliveryTime: str

    """
    This field will return a success message if the money transferred successfully.
    """
    message: str

    """
    This is a unique system reference number assigned to the transaction.
    """
    system_reference_number: str

    """
    This field contains the unique payment ID.
    """
    payment_id: Optional[str] = None
