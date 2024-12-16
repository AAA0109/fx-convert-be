from abc import ABC, abstractmethod

from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.margin.models.margin import MarginDetail


class MarginDetailServiceInterface(ABC):

    @abstractmethod
    def get_margin_detail(self, company: Company, date: Date) -> MarginDetail:
        raise NotImplementedError()


class DbMarginDetailService(MarginDetailServiceInterface):

    def get_margin_detail(self, company: Company, date: Date) -> MarginDetail:
        return MarginDetail.objects.get(company=company, date=date)
