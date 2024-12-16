from typing import Optional
from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.models import Quote


class OrderQuoteService():
    """ Service to create and update order quote """
    def create_quote(self, company: Company, currency_from_mnemonic: str, currency_to_mnemonic: str, user: Optional[User] = None) -> Quote:
        pair = self.__get_pair(currency_from_mnemonic=currency_from_mnemonic,
                               currency_to_mnemonic=currency_to_mnemonic)
        quote = Quote.create_quote(company=company, pair=pair, user=user)
        return quote

    def __get_pair(self, currency_from_mnemonic: str, currency_to_mnemonic: str) -> FxPair:
        from_currency = Currency.get_currency(currency=currency_from_mnemonic)
        to_currency = Currency.get_currency(currency=currency_to_mnemonic)
        pair = FxPair.get_pair_from_currency(
            base_currency=from_currency, quote_currency=to_currency)
        if not pair:
            pair = FxPair(
                base_currency=from_currency,
                quote_currency=to_currency
            )
        return pair
