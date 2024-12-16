from dataclasses import dataclass, fields
from typing import Iterable, List, Optional, Dict

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


# Bene Add
# ========================================

@dataclass
class BeneAddPayload(JsonDictMixin):
    _getPage: Optional[int] = 1
    _getCommon: Optional[int] = 1
    _getUserCommon: Optional[int] = 1


@dataclass
class BeneAddCurrency(JsonDictMixin):
    id: int
    code: str
    precision: int
    isEnabled: bool
    isExotics: bool
    country: Optional[str] = ''


@dataclass
class BeneAddCommon(JsonDictMixin):
    currencies: Iterable[BeneAddCurrency]


@dataclass
class BeneAddUser(JsonDictMixin):
    id: int
    name: str
    email: str
    fullName: str
    createdViaWizard: bool
    spokenWithTempus: bool
    menuitems: Optional[str] = None


@dataclass
class BeneAddEntity(JsonDictMixin):
    id: int
    number: str
    name: str
    dummy: bool
    stub: bool
    createdViaWizard: bool
    complianceStatus: str


@dataclass
class BeneAddCountry(JsonDictMixin):
    id: int
    name: str
    code: str


@dataclass
class BeneAddUserCommon(JsonDictMixin):
    user: BeneAddUser
    entity: BeneAddEntity



@dataclass
class BeneAddPurpose(JsonDictMixin):
    id: int
    name: str


@dataclass
class BeneAddBankCode(JsonDictMixin):
    title: str
    validationMode: str
    type: str
    isRequired: bool


@dataclass
class BeneAddRoutingOption(JsonDictMixin):
    opts: Iterable[str]
    id: int
    type: str
    bankCodes: Iterable[BeneAddBankCode]
    accountNumberMinLength: Optional[int] = None
    accountNumberMaxLength: Optional[int] = None
    validBeneCountryIds: Optional[Iterable[int]] = None
    validBankCountryIds: Optional[Iterable[int]] = None


@dataclass
class BeneAddRoutingType(JsonDictMixin):
    id: int
    name: str


@dataclass
class BeneAddRoutingCodeType(JsonDictMixin):
    title: str
    validationMode: str


@dataclass
class BeneAddAccountNumberType(JsonDictMixin):
    title: str
    validationMode: str


@dataclass
class BeneAddRoutingConfig(JsonDictMixin):
    ccyRoutingOptionsMap: Dict[str, Iterable[BeneAddRoutingOption]]
    routingTypes: Iterable[BeneAddRoutingType]
    routingCodeTypes: Dict[str, BeneAddRoutingCodeType]
    accountNumberTypes: Dict[str, BeneAddAccountNumberType]


@dataclass
class BeneAddPage(JsonDictMixin):
    entities: Iterable[BeneAddEntity]
    countries: Iterable[BeneAddCountry]
    purposes: Iterable[BeneAddPurpose]
    routingConfig: BeneAddRoutingConfig
    routeOptsMap: Dict[str, Iterable[BeneAddRoutingOption]]
    routingCodeTypes: Iterable[str]
    ccyIdsAllowEdit: Iterable[int]
    disallowedCountries: Iterable[int]
    allowEditSwift: bool
    hasAccessPayments: bool
    maxBankInstructionsLen: int
    countryIdsWithRequiredProvince: Iterable[int]
    countryIdsWithRequiredPostal: Iterable[int]


@dataclass
class BeneAddResponse(JsonDictMixin):
    common: BeneAddCommon
    userCommon: BeneAddUserCommon
    page: BeneAddPage
    err: Optional[str] = None
    errType: Optional[str] = None

    def __post_init__(self):
        currencies = []
        for currency in self.common['currencies']:
            currencies.append(BeneAddCurrency(**currency))
        self.common = BeneAddCommon(currencies=currencies)

# ========================================


# Bene Get Bank
# ========================================

@dataclass
class BeneGetBankPayload(JsonDictMixin):
    accountNumber: str
    accountNumberType: str
    type: str
    countryId: int
    currencyCode: str
    routingCodeType: Optional[str]
    routingCode: Optional[str]


@dataclass
class BeneGetBankResponse(JsonDictMixin):
    name: str
    country: str
    city: str
    postCode: str
    swift: str
    aba: bool
    bsb: bool
    sortCode: bool
    transitCode: bool
    ach: bool
    routingTypeId: int
    routingCodeType: str
    accountNumberType: str
    routingCode: str
    bankCode: str
    countryId: int
    address1: str
    isRoutingCodeFake: bool
    type: str
    key: str
    address2: Optional[str] = None
    province: Optional[str] = None


# ========================================
# Bene Save
# ========================================

@dataclass
class BaseBeneSaveBank(JsonDictMixin):
    routingCode: Optional[str] = ''
    routingCodeType: Optional[str] = ''
    accountNumber: Optional[str] = ''
    accountNumberType: Optional[str] = ''
    name: Optional[str] = ''
    address1: Optional[str] = ''
    address2: Optional[str] = ''
    city: Optional[str] = ''
    province: Optional[str] = ''
    countryId: Optional[int] = None
    syncCountryId: Optional[bool] = False
    postCode: Optional[str] = ''
    instructions: Optional[str] = ''
    key: Optional[str] = ''
    type: Optional[str] = ''

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)

@dataclass
class BeneSaveMainBank(BaseBeneSaveBank):

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)

@dataclass
class BeneSaveInterBank(BaseBeneSaveBank):

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)


@dataclass
class BeneSavePayload(JsonDictMixin):
    currencyId: int
    name: str
    nickname: str
    countryId: int
    address1: str
    address2: str
    city: str
    postal: str
    email: str
    purposeId: int
    purposeDescription: str
    mainBank: BeneSaveMainBank
    id: Optional[int] = None
    interBank: Optional[BeneSaveInterBank] = None
    furtherName: Optional[str] = ''
    furtherAccountNumber: Optional[str] = ''
    province: Optional[str] = ''

# ========================================

# ========================================
# Bene List
# ========================================
@dataclass
class BeneListPayload(JsonDictMixin):
    sort: str
    dir: str
    page: int
    limit: int
    entityId: int
    search: str
    currencyId: int
