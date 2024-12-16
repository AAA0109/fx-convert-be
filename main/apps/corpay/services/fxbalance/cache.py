import logging
from abc import ABC

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings, FXBalance, FXBalanceDetail, FXBalanceAccount, \
    FXBalanceAccountSettlementInstruction
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams, \
    FxBalanceHistoryParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models import Currency

logger = logging.getLogger(__name__)


class CorPayFXBalanceCacheService(ABC):
    def __init__(self):
        self.corpay_service = CorPayService()
        self.currencies = {c.mnemonic: c for c in Currency.get_currencies()}

    def execute(self, company_id=None):
        credentials = CorpaySettings.objects.all()
        company_ids = [credential.company.pk for credential in credentials]
        companies = Company.objects.filter(pk__in=company_ids)
        if company_id:
            companies = companies.filter(pk=company_id)

        for company in companies:
            try:
                self.handle_single(company)
            except Exception as e:
                logger.exception(e)

    def handle_single(self, company: Company):
        self.corpay_service.init_company(company)
        logger.debug(f"Getting FXBalance accounts for company - {company.name} - ID: {company.pk}")
        params = ViewFXBalanceAccountsParams(
            includeBalance=True
        )
        response = self.corpay_service.list_fx_balance_accounts(params)
        for row in response['data']['rows']:
            currency = Currency.get_currency(row['currency'])
            # Update or create LinkBalanceAccount
            fx_balance_account, created = FXBalanceAccount.objects.update_or_create(
                account_number=row['accountNumber'],
                company=company,
                defaults={
                    'description': row.get('description', ''),
                    'account': row.get('account', ''),
                    'currency': currency,
                    'ledger_balance': row.get('ledgerBalance', 0),
                    'balance_held': row.get('balanceHeld', 0),
                    'available_balance': row.get('availableBalance', 0),
                    'client_code': row.get('clientCode', ''),
                    'client_division_id': row.get('clientDivisionId', '')
                }
            )

            # Update or create SettlementInstruction for the LinkBalanceAccount
            settlement_instructions = row.get('settlementInstructions', {})
            settlement_instructions_currency = Currency.get_currency(settlement_instructions.get('curr', ''))
            FXBalanceAccountSettlementInstruction.objects.update_or_create(
                fx_balance_account=fx_balance_account,
                defaults={
                    'is_na_associated': settlement_instructions.get('isNAAssociated', False),
                    'incoming_account_number': settlement_instructions.get('incomingAccountNumber', ''),
                    'currency': settlement_instructions_currency,
                    'curr_name': settlement_instructions.get('currName', ''),
                    'is_iban': settlement_instructions.get('isIBAN', False),
                    'bene_info': settlement_instructions.get('beneInfo', '').strip() if settlement_instructions.get(
                        'beneInfo') else '',
                    'bank_name': settlement_instructions.get('bankName', '').strip() if settlement_instructions.get(
                        'bankName') else '',
                    'bank_address': settlement_instructions.get('bankAddress',
                                                                '').strip() if settlement_instructions.get(
                        'bankAddress') else '',
                    'bank_swift': settlement_instructions.get('bankSwift', '').strip() if settlement_instructions.get(
                        'bankSwift') else ''
                }
            )

        for item in response['items']:
            account_number = item['id']

            currency = Currency.get_currency(item['curr'])
            if currency is None:
                logger.error(f"Currency {item['curr']} not found!")
                continue

            history_params = FxBalanceHistoryParams(
                includeDetails=True
            )
            history_response = self.corpay_service.list_fx_balance_history(
                fx_balance_id=account_number,
                data=history_params
            )

            for row in history_response['data']['rows']:
                balance, _ = FXBalance.objects.update_or_create(
                    account_number=account_number,
                    order_number=row['orderNumber'],
                    company=company,
                    defaults=dict(
                        date=row['date'],
                        amount=row.get('amount', 0),
                        currency=self.currencies.get(item['curr'], None),
                        debit_amount=row.get('debitAmount', 0),
                        credit_amount=row.get('creditAmount', 0),
                        is_posted=row.get('isPosted', False),
                        balance=row.get('balance', 0),
                        status=FXBalance.FXBalanceStatus.COMPLETE,
                    ))

                if row.get('details'):
                    for detail in row['details']:
                        detail_currency = Currency.get_currency(detail.get('currency', ''))

                        if detail_currency is None:
                            logger.error(f"Detail currency: {detail.get('currency')} not found!")
                            continue

                        FXBalanceDetail.objects.update_or_create(
                            fx_balance=balance,
                            transaction_id=detail.get('transID', ''),
                            order_number=detail.get('orderNumber', ''),
                            defaults=dict(
                                identifier=detail.get('identifier', '').strip() if detail.get('identifier') else '',
                                name=detail.get('name', '').strip() if detail.get('name') else '',
                                currency=detail_currency,
                                amount=detail.get('amount', 0),
                                date=detail.get('date', None),
                            )
                        )
