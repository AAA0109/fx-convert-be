from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


class BankSource(Enum):
    DBS_HK = "DBS_HK"
    DBS_SG = "DBS_SG"
    DBS_ID = "DBS_ID"
    JPM_SG = "JPM_SG"
    JPM_AU = "JPM_AU"
    JPM_UK = "JPM_UK"
    JPM_CA = "JPM_CA"
    MONOOVA_AU = "MONOOVA_AU"
    BOL_LT = "BOL_LT"
    CB_GB = "CB_GB"
    CFSB_US = "CFSB_US"
    BARCLAYS_UK = "BARCLAYS_UK"
    BARCLAYS_EU = "BARCLAYS_EU"
    CITI_SG = "CITI_SG"
    CITI_MX = "CITI_MX"
    CFSB_USINTL = "CFSB_USINTL"
    GMO_JP = "GMO_JP"
    NETBANK_PH = "NETBANK_PH"
    GOCARDLESS = "GOCARDLESS"
    DIRECTFAST_SG = "DIRECTFAST_SG"
    BANKINGCIRCLE_PL = "BANKINGCIRCLE_PL"
    COLUMN = "COLUMN"


@dataclass
class SimulateRcvTrxPayload(JsonDictMixin):
    """
    The amount of the transaction to simulate.
    """
    amount: float

    """
    This field contains the bank reference number.
    """
    bankReferenceNumber: str

    """
    This field details the source of the funds.
    """
    bankSource: BankSource

    """
    This field contains the country.
    """
    country: str

    """
    This field contains the 3-letter currency code.
    """
    currency:str

    """
    This object accepts additional information about the corridor being used.
    """
    additionalInfo: Optional[dict] = None

    """
    This field contains bank's branch code.
    """
    branchCode: Optional[str] = None

    """
    This field contains the expiry time for ICC.
    """
    iccExpiry: Optional[str] = None

    """
    This field contains the payment instruction type
    """
    instructionType: Optional[str] = None

    """
    This field contains the narrative.
    """
    narrative: Optional[str] = None

    """
    This field details the payment mode.
    """
    payMode: Optional[str] = None

    """
    This field contains the remitter account number.
    """
    remitterAccountNumber: Optional[str] = None

    """
    This field contains the remitter bank code.
    """
    remitterBankCode: Optional[str] = None

    """
    This field contains the remitter bank name.
    """
    remitterBankName: Optional[str] = None

    """
    This field contains the remitter name.
    """
    remitterName: Optional[str] = None

    """
    This field contains the remitter name local language.
    """
    remitterNameLocalLanguage: Optional[str] = None

    """
    This field contains the transaction reference number/ID.
    """
    transactionId: Optional[str] = None

    """
    This field contains the ICC transaction source.
    """
    transactionSource: Optional[str] = None

    """
    This field contains the ICC entry type.
    """
    type: Optional[Literal['CREDIT', 'DEBIT']] = None

    """
    This field contains the virtual account number.
    """
    virtualAccountNumber: Optional[str] = None
