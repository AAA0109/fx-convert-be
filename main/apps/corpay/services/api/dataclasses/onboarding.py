from typing import List, Optional
from dataclasses import dataclass

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin

@dataclass
class CompanyDirector(JsonDictMixin):
    """Director or senior officer full legal name"""
    fullName: str
    """Director or senior officer job title"""
    jobTitle: str
    """Director or senior officer occupation"""
    occupation: str


@dataclass
class BeneficialOwner(JsonDictMixin):
    """Beneficial Owner full legal name"""
    fullName: str
    """Beneficial Owner nationality"""
    nationality: str
    """Beneficial Owner Social security number"""
    ssn: str
    """Beneficial Owner residential address"""
    residentialAddress: str
    """Beneficial ownership percentage"""
    ownershipPercentage: float
    """Beneficial owner date of birth"""
    beneficialOwnerDOB: Optional[str] = None


@dataclass
class OnboardingRequestBody(JsonDictMixin):
    """Client's complete legal name to be onboarded"""
    companyName: str
    """Current business address"""
    companyStreetAddress: str
    """Current business location - city/town/suburb"""
    companyCity: str
    """Current business zip/postal code"""
    companyPostalCode: str
    """Current business country code (2 character ISO code)
    For a list of valid values run GET /api/countries"""
    companyCountryCode: str
    """Registered current business phone number"""
    businessContactNumber: str
    """Registered current business email for confirmation"""
    businessConfirmationEmail: str
    """Current business Registration/Incorporation Number/ACN/ABN Number/Unique Entity Number (UEN)"""
    businessRegistrationIncorporationNumber: str
    """Legal structure of the company.
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=ApplicantType
    SeeReference Datafolder for more details."""
    applicantTypeId: str
    """The type of business (any primary and secondary activities)
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=NatureOfBusiness
    SeeReference Datafolder for more details."""
    natureOfBusiness: str
    """Purpose of transactions id.
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=PurposeOfTransaction
    SeeReference Datafolder for more details."""
    purposeOfTransactionId: str
    """Currencies needed (3 character currency code, comma separated)
    For a list of valid values run GET /api/payCurrencies?product=QuickQuote"""
    currencyNeeded: str
    """Approximate per trade volumes.
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=TradeVolumeRange
    SeeReference Datafolder for more details."""
    tradeVolume: str
    """Approximate Annual Volume.
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=AnnualVolumeRange
    SeeReference Datafolder for more details."""
    annualVolume: str
    """Countries to which funds transfer are expected to go to (2 character country code, comma separated)
    For a list of valid values run GET /api/countries"""
    fundDestinationCountries: str
    """Countries which funds transfer are expected to come from (2 character country code, comma separated)
    For a list of valid values run GET /api/countries"""
    fundSourceCountries: str
    """Director or senior officer full legal name"""
    companyDirectors: List[CompanyDirector]
    """Does any individual own 25% or more ownership of the company
    TRUE/ FALSE"""
    anyIndividualOwn25PercentOrMore: bool
    """All statements in this Agreement, and any other information and documentation submitted in support of this Agreement, are true and correct.
    TRUE/ FALSE
    Note: The value must be true to complete onboarding request."""
    provideTruthfulInformation: bool
    """Client has read, understood and hereby accepts the attached terms and conditions -https://cross-border.corpay.com/tc/
    TRUE/ FALSE
    Note: The value must be true to complete onboarding request."""
    agreeToTermsAndConditions: bool
    """Consent to Privacy Notice athttps://payments.corpay.com/compliance
    TRUE/ FALSE
    Note: The value must be true to complete onboarding request."""
    consentToPrivacyNotice: bool
    """The individual(s) signing this application have the authority to bind the Client to the terms of this Agreement (supporting documentation may be requested)
    TRUE/ FALSE
    Note: The value must be true to complete onboarding request."""
    authorizedToBindClientToAgreement: bool
    """Signatory full name
    Note: At least 1 Signatory is Required. In case the country is Australia two Signatories are required."""
    signerFullName: str
    """Signatory date of birth
    Allowed format: mm/dd/yyyy"""
    signerDateOfBirth: str
    """Signatory job title"""
    signerJobTitle: str
    """Signatory email"""
    signerEmail: str
    """Complete address of the signatory (Street, City/Town, State/Province, Country, and Zip/Postal Code)"""
    signerCompleteResidentialAddress: str

    # Optional fields
    """DBA/Registered Trade name/ Business name (if applicable)"""
    DBAOrRegisteredTradeName: Optional[str] = None
    """Current business location -state/province.
    For a list of valid values run GET /api/regions?Country=US"""
    companyState: Optional[str] = None
    """Alternative current registered business email for confirmation"""
    businessConfirmationEmail2: Optional[str] = None
    """Does the company publicly trade? TRUE/ FALSE"""
    isPubliclyTraded: Optional[bool] = None
    """Stock Exchange Symbol"""
    stockSymbol: Optional[str] = None
    """The country code in which the current company is incorporated or legally registered (2 character ISO code)
    For a list of valid values run GET /api/countries"""
    formationIncorportationCountryCode: Optional[str] = None
    """The state/province in which the current company is incorporated or legally registered
    For a list of valid values run GET /api/regions?Country=US"""
    formationIncorportationState: Optional[str] = None
    """Tax ID/EIN/VAT/GST Registration number"""
    taxIDEINNumber: Optional[str] = None
    """Type of company to be onboarded.
    For a list of valid values run GET /api/clientonboarding/onboardingpicklists?pickListType=BusinessType
    SeeReference Datafolder for more details."""
    businessTypeId: Optional[str] = None
    """Current business website URL"""
    websiteUrl: Optional[str] = None
    """Is the company owned by other corporate entity?TRUE/ FALSE"""
    ownedByOtherCorporateEntity: Optional[bool] = None
    """Does the company publicly trade? TRUE/ FALSE"""
    ownedByPubliclyTradedCompany: Optional[bool] = None
    """Stock Exchange Symbol of owning entity"""
    ownedByPubliclyTradedCompanyStockSymbol: Optional[str] = None
    """Beneficial Owner full legal name"""
    beneficialOwners: Optional[List[BeneficialOwner]] = None
    """Second Signatory full name"""
    secondSignerFullName: Optional[str] = None
    """Second signatory date of birth
    Allowed format: mm/dd/yyyy"""
    secondSignerDateOfBirth: Optional[str] = None
    """Second signatory job title"""
    secondSignerJobTitle: Optional[str] = None
    """Second signatory email"""
    secondSignerEmail: Optional[str] = None
    """Complete address of the second signatory (Street, City/Town, State/Province, Country, and Zip/Postal Code)"""
    secondSignerCompleteResidentialAddress: Optional[str] = None


@dataclass
class OnboardingPickListParams(JsonDictMixin):
    """Available Options are: AnnualVolumeRange, ApplicantType, BusinessType, PurposeOfTransaction, NatureOfBusiness"""
    pickListType: str


@dataclass
class OnboardingAuthSecretKeyParams(JsonDictMixin):
    onboardingId: str
