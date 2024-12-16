from typing import Iterable

from main.apps.account.models import Company
from main.apps.billing.models import Fee


class FeeService:
    def get_fees(self, company: Company) -> Iterable[Fee]:
        return Fee.objects.filter(company=company)

