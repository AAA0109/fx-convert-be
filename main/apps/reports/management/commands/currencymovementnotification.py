from django.core.management import BaseCommand

from main.apps.account.models.company import Company
from main.apps.reports.services import CurrencyMovementNotification


class Command(BaseCommand):
    help = "Notify stack for the abnormal movements on currency for companies"

    def add_arguments(self, parser):
        parser.add_argument("company_id", nargs="?", type=int)

    def handle(self, *args, **options):
        companies = Company.objects.filter(status=Company.CompanyStatus.ACTIVE)

        if company_id := options.get('company_id'):
            companies = companies.filter(pk=company_id)

        if not companies.count():
            return None

        CurrencyMovementNotification(companies=companies).send()
