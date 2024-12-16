from typing import Union

from main.apps.account.models.company import Company
from main.apps.oems.models.quote import Quote


class QuoteUtil:

    @staticmethod
    def clean_quote_data(company:Union[str, int, Company]):
        if isinstance(company, str) and company == 'all':
            companies = Company.objects.all()
            for cmp in companies:
                Quote.objects.filter(company=cmp).delete()
        else:
            cmp = company
            if isinstance(company, int):
                try:
                    cmp = Company.objects.get(id=company)
                except Company.DoesNotExist:
                    cmp = None

            if cmp:
                Quote.objects.filter(company=cmp).delete()
