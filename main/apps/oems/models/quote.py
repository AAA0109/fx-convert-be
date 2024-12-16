from typing import Optional, Union
from django.db import models
from django_extensions.db.models import TimeStampedModel
from main.apps.currency.models.currency import Currency

from main.apps.util import get_or_none
from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.currency.models.fxpair import FxPair


class Quote(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="quote_company")
    pair = models.ForeignKey(FxPair, on_delete=models.PROTECT, related_name="quote_pair", null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="quote_user", null=True)
    from_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="quote_from_currency", null=True)
    to_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="quote_to_currency", null=True)

    @staticmethod
    def create_quote(company: Company, pair: FxPair, user: Optional[User]) -> 'Quote':
        if pair.pk:
            quote = Quote(
                company=company,
                pair=pair,
                from_currency=pair.base_currency,
                to_currency=pair.quote_currency,
                user=user
            )
        else:
            quote = Quote(
                company=company,
                from_currency=pair.base_currency,
                to_currency=pair.quote_currency,
                user=user
            )
        quote.save()
        return quote

    @staticmethod
    @get_or_none
    def get_quote(quote_id: int) -> 'Quote':
        quote = Quote.objects.get(pk=quote_id)
        return quote

    class NotFound(Exception):
        def __init__(self, quote_id: Union[int, str, 'Quote']):
            if isinstance(quote_id, int):
                super(Quote.NotFound, self) \
                    .__init__(f"Quote with id:{quote_id} is not found")
            elif isinstance(quote_id, str):
                super(Quote.NotFound, self) \
                    .__init__(f"Quote with name:{quote_id} is not found")
            elif isinstance(quote_id, Quote):
                super(Quote.NotFound, self) \
                    .__init__(f"Quote:{quote_id} is not found")
            else:
                super(Quote.NotFound, self).__init__()
