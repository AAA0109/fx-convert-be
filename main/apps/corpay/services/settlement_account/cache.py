import logging
from abc import ABC

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.models.settlement_account import SettlementAccount
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models import Currency

logger = logging.getLogger(__name__)


class CorPaySettlementAccountCacheService(ABC):
    def __init__(self):
        self.corpay_service = CorPayService()

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
        response = self.corpay_service.list_settlement_accounts()
        for item in response['items']:
            for children in item['children']:
                currency = Currency.get_currency(children['currency'])
                if currency is None:
                    logger.error(f"Currency {children['currency']} not found!")
                    continue

                settlement_account, created = SettlementAccount.objects.update_or_create(
                    settlement_account_id=children['id'],
                    company=company,
                    defaults={
                        'delivery_method': children.get('method', {}).get('id', ''),
                        'currency': currency,
                        'text': children.get('text', ''),
                        'payment_ident': children.get('paymentIdent', '').strip() if children.get(
                            'paymentIdent') else '',
                        'bank_name': children.get('bankName', ''),
                        'bank_account': children.get('bankAccount', '').strip() if children.get('bankAccount') else '',
                        'preferred': children.get('preferred', False),
                        'selected': children.get('selected', False),
                        'category': item.get('text', '')
                    }
                )
                if created:
                    logger.debug(f"Settlement account created ({settlement_account.pk})")
                else:
                    logger.debug(f"Settlement account updated ({settlement_account.pk})")
