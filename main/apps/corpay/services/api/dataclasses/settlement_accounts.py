import datetime
from dataclasses import dataclass
from typing import List

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin

@dataclass
class ViewFXBalanceAccountsParams(JsonDictMixin):
    """{search string; optional}"""
    searchString: str = None
    """Display 'ledgerBalance', 'balanceHeld', and 'availableBalance' values; optional"""
    includeBalance: bool = True


@dataclass
class FxBalanceHistoryParams(JsonDictMixin):
    """Sort direction, can be 'asc' or 'desc'"""
    sort: str = 'asc'
    """from date, in format of YYYY-MM-DD"""
    fromDate: datetime.date = None
    """to date, in format of YYYY-MM-DD"""
    toDate: datetime.date = None
    """number of objects to skip; optiona"""
    skip: int = None
    """number of objects to retrieve; optional"""
    take: int = None
    """Displays funds distribution data"""
    includeDetails: bool = None


@dataclass
class CreateFXBalanceAccountsBody(JsonDictMixin):
    """List of Three-letter ISO currency code"""
    currencies: List
    """Name of the account"""
    account: str = None
