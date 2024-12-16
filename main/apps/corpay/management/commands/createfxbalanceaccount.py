from django.core.management import BaseCommand

from main.apps.account.models import Company
from main.apps.corpay.services.fxbalance.account_creator import CorPayFxBalanceAccountCreator
from main.apps.corpay.models.currency import CurrencyDefinition
class Command(BaseCommand):
    help = "Command for creating CorPay FX Balance Accounts"

    def add_arguments(self, parser):
        parser.add_argument("--company_id", type=int)
        parser.add_argument("--currencies", nargs="?", type=str, default=None)

    def handle(self, *args, **options):
        company_id = options['company_id']
        company = Company.objects.get(pk=company_id)
        if 'currencies' in options:
            currencies = [currency.strip() for currency in options['currencies'].split(',')]
        else:
            currencies = [currency.mnemonic for currency in CurrencyDefinition.get_all_wallet_api_currencies()]
        service = CorPayFxBalanceAccountCreator()
        service.create(company=company, currencies=currencies)
