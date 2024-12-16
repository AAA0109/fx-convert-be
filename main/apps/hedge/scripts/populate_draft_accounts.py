from main.apps.corpay.models import ForwardQuote, DestinationAccountType
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
import logging

logger = logging.getLogger(__name__)


def get_fx_balance_account_from_currency(accounts, currency):
    return next((item for item in accounts['items'] if item['curr'] == currency), None)

def get_settlement_account_from_currency(accounts, currency):
    return next((item for item in accounts['items'][1]['children'] if item['currency'] == currency), None)
def run():
    fx_balance_accounts_cache = {}
    settlement_account_cache = {}
    for draft in DraftFxForwardPosition.objects.all():
        draft_cashflow = draft.draft_cashflow
        cashflow = draft.cashflow
        if cashflow is None and draft_cashflow is None:
            logger.error(f"No cashflow or draft cashflow found for {draft.pk}")
            continue
        if draft_cashflow is None:
            company = cashflow.account.company
        else:
            company = draft_cashflow.company
        if company is None:
            logger.error(f"Unable to find company for draft: {draft.pk}")

        corpay_service = CorPayService()
        corpay_service.init_company(company)

        if company.pk not in fx_balance_accounts_cache:
            params = ViewFXBalanceAccountsParams(includeBalance=False)
            fx_balance_accounts = corpay_service.list_fx_balance_accounts(params)
            fx_balance_accounts_cache.setdefault(company.pk, fx_balance_accounts)
        else:
            fx_balance_accounts = fx_balance_accounts_cache[company.pk]

        if company.pk not in settlement_account_cache:
            settlement_accounts = corpay_service.list_settlement_accounts()
            settlement_account_cache.setdefault(company.pk, settlement_accounts)
        else:
            settlement_accounts = settlement_account_cache[company.pk]

        _cashflow = draft_cashflow
        if _cashflow is None:
            _cashflow = cashflow
        currency = _cashflow.currency
        if _cashflow.amount > 0:
            origin_account = get_fx_balance_account_from_currency(fx_balance_accounts, currency.mnemonic)
            if origin_account is None:
                logger.error(f"Unable to get origin account for currency: {currency.mnemonic}")
            destination_account = get_fx_balance_account_from_currency(fx_balance_accounts, 'USD')
            funding_account = get_settlement_account_from_currency(settlement_accounts, currency.mnemonic)
            if funding_account is None:
                logger.error(f"Unable to get funding account for currency: {currency.mnemonic}")
        else:
            origin_account = get_fx_balance_account_from_currency(fx_balance_accounts, 'USD')
            destination_account = get_fx_balance_account_from_currency(fx_balance_accounts, currency.mnemonic)
            if destination_account is None:
                logger.error(f"Unable to get destination account for currency: {currency.mnemonic}")
            funding_account = get_settlement_account_from_currency(settlement_accounts, 'USD')

        should_save = False

        if origin_account is not None and draft.origin_account is None:
            logger.debug(
                f"Origin account missing for draft: {draft.pk}, Updating origin account to {origin_account['text']}"
            )
            draft.origin_account = origin_account['text']
            should_save = True

        if destination_account is not None and draft.destination_account is None:
            logger.debug(
                f"Destination account missing for draft: {draft.pk}, "
                f"Updating destination account to {destination_account['text']}"
            )
            draft.destination_account = destination_account['text']
            should_save = True

        if destination_account is not None and draft.destination_account == destination_account['text']:
            draft.destination_account_type = DestinationAccountType.C
            should_save = True

        if funding_account is not None and funding_account is not None:
            draft.funding_account = funding_account['text']
            should_save = True

        if draft.is_cash_settle and draft.cash_settle_account is None and destination_account is not None:
            draft.cash_settle_account = destination_account['text']
            should_save = True

        if draft.purpose_of_payment is None:
            draft.purpose_of_payment = 'PURCHASE OF GOOD(S)'
            should_save = True

        if should_save:
            draft.save()

        if draft.cashflow is not None:
            quotes = ForwardQuote.objects.filter(cashflow=draft.cashflow)
            for quote in quotes:
                try:
                    forward = quote.forward
                    forward.destination_account_type = draft.destination_account_type
                    forward.destination_account = draft.destination_account
                    forward.origin_account = draft.origin_account
                    forward.is_cash_settle = draft.is_cash_settle
                    forward.cash_settle_account = draft.cash_settle_account
                    forward.purpose_of_payment = draft.purpose_of_payment
                    forward.save()
                except Exception as e:
                    logger.error(f"Unable to save forward: {e}")



