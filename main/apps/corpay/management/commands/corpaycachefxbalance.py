import logging

from django.core.management import BaseCommand, CommandError

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.services.fxbalance.cache import CorPayFXBalanceCacheService


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", nargs="?", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to cache CorPay FXAccount balance"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            companies = []
            if 'company_id' in options and options['company_id'] is not None:
                company_id = options["company_id"]
                company = Company.objects.get(pk=company_id)
                if not company:
                    raise CommandError("Company does not exist")
                companies.append(company)
            else:
                for settings in CorpaySettings.objects.all():
                    companies.append(settings.company)
            for company in companies:
                logging.info(f"Running to cache CorPay FXAccount balance for (ID={company.pk}).")

                service = CorPayFXBalanceCacheService()
                service.execute(company.pk)

                logging.info(f"Finished cache CorPay FXAccount balance for (ID={company.pk}).")
                logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
