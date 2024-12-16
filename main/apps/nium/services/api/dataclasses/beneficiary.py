from dataclasses import dataclass, fields
from typing import Optional

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class BeneficiaryValidationSchemaParams(JsonDictMixin):
    payoutMethod: Optional[str] = None


@dataclass
class ListBeneficiaryParams(JsonDictMixin):
    beneficiaryAccountNumber: Optional[str] = None
    beneficiaryName: Optional[str] = None
    destinationCurrency: Optional[str] = None
    payoutMethod: Optional[str] = None


@dataclass
class BeneAccountVerifyV2(JsonDictMixin):
    name: str
    status: str


@dataclass
class BeneCardMetaDataV2(JsonDictMixin):
    cardTypeCode: str
    billingCurrencyCode: str
    billingCurrencyMinorDigits: str
    issuerName: str
    cardIssuerCountryCode: str
    fastFundsIndicator: str
    pushFundsBlockIndicator: str
    onlineGamblingBlockIndicator: str
    isCardValid: bool
    isBankSupported: bool


@dataclass
class BeneResponseV2(JsonDictMixin):
    beneficiaryHashId: str
    beneficiaryName: str
    beneficiaryContactCountryCode: str
    beneficiaryContactNumber: str
    beneficiaryAccountType: str
    beneficiaryEmail: str
    remitterBeneficiaryRelationship: str
    beneficiaryAddress: str
    beneficiaryCountryCode: str
    beneficiaryState: str
    beneficiaryCity: str
    beneficiaryPostcode: str
    beneficiaryCreatedAt: str
    beneficiaryUpdatedAt: str
    payoutHashId: str
    destinationCountry: str
    destinationCurrency: str
    beneficiaryBankName: str
    beneficiaryBankAccountType: str
    beneficiaryAccountNumber: str
    beneficiaryBankCode: str
    routingCodeType1: str
    routingCodeValue1: str
    routingCodeType2: str
    routingCodeValue2: str
    payoutMethod: str
    beneficiaryIdentificationType: str
    beneficiaryIdentificationValue: str
    payoutCreatedAt: str
    payoutUpdatedAt: str
    beneficiaryCardType: str
    beneficiaryCardToken: str
    beneficiaryCardNumberMask: str
    beneficiaryCardIssuerName: str
    beneficiaryCardExpiryDate: str
    beneficiaryCardMetaData: BeneCardMetaDataV2
    proxyType: str
    proxyValue: str


@dataclass
class AddBeneResponseV2(BeneResponseV2):
    accountVerification: BeneAccountVerifyV2
    autosweepPayoutAccount: bool
    beneficiaryContactName: str
    beneficiaryDob: str
    beneficiaryEntityType: str
    beneficiaryEstablishmentDate: str
    defaultAutosweepPayoutAccount: bool


@dataclass
class DetailBeneResponseV2(AddBeneResponseV2):
    pass


@dataclass
class UpdateBeneResponseV2(BeneResponseV2):
    pass


@dataclass
class AddBenePayloadV2(JsonDictMixin):
    beneficiaryAccountNumber: str
    beneficiaryAccountType: str
    beneficiaryAddress: str
    beneficiaryAlias: str
    beneficiaryBankAccountType: str
    beneficiaryCity: str
    beneficiaryCountryCode: str
    beneficiaryName: str
    destinationCurrency: str
    payoutMethod: str
    authenticationCode: Optional[str] = None
    autoSweepPayoutAccount: Optional[bool] = None
    beneficiaryBankCode: Optional[str] = None
    beneficiaryBankName: Optional[str] = None
    beneficiaryCardExpiryDate: Optional[str] = None
    beneficiaryCardIssuerName: Optional[str] = None
    beneficiaryContactCountryCode: Optional[str] = None
    beneficiaryContactName: Optional[str] = None
    beneficiaryContactNumber: Optional[str] = None
    beneficiaryDob: Optional[str] = None
    beneficiaryEmail: Optional[str] = None
    beneficiaryEntityType: Optional[str] = None
    beneficiaryEstablishmentDate: Optional[str] = None
    beneficiaryIdentificationType: Optional[str] = None
    beneficiaryIdentificationValue: Optional[str] = None
    beneficiaryPostcode: Optional[str] = None
    beneficiaryState: Optional[str] = None
    convertDestinationCurrency: Optional[str] = None
    defaultAutoSweepPayoutAccount: Optional[str] = None
    destinationCountry: Optional[str] = None
    encryptedBeneficiaryCardToken: Optional[str] = None
    proxyType: Optional[str] = None
    proxyValue: Optional[str] = None
    remitterBeneficiaryRelationship: Optional[str] = None
    routingCodeType1: Optional[str] = None
    routingCodeType2: Optional[str] = None
    routingCodeValue1: Optional[str] = None
    routingCodeValue2: Optional[str] = None

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)

@dataclass
class UpdateBenePayloadV2(AddBenePayloadV2):

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)
