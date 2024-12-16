import logging

from django.core.management import BaseCommand

from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams
from main.apps.corpay.services.corpay import CorPayService

logger = logging.getLogger(__name__)
class Command(BaseCommand):
    help = "Django command to show CorPay FXAccount balance"

    def handle(self, *args, **options):
        try:
            balance_total = 0
            for settings in CorpaySettings.objects.all():
                company = settings.company
                corpay_service = CorPayService()
                corpay_service.init_company(company)
                logger.info(f"Showing balance for {company.name} ({company.pk})")
                data = ViewFXBalanceAccountsParams(
                    includeBalance=True
                )
                response = corpay_service.list_fx_balance_accounts(data=data)
                wallet_balance = 0
                for item in response['items']:
                    if item['id'] == settings.fee_wallet_id:
                        wallet_balance = item['availableBalance']
                        balance_total += item['availableBalance']
                logger.info(f"Fee wallet balance: {wallet_balance}")
            logger.info(f"------------------------------")
            logger.info(f"Total balance: {balance_total}")
        except Exception as ex:
            logging.error(ex)
