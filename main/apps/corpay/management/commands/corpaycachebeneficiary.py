import logging

from django.core.management import BaseCommand, CommandError

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.services.beneficiary.cache import CorPayBeneficiaryCacheService


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", nargs="?", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to cache CorPay Beneficiary"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]
            logging.info(f"Running to cache CorPay Beneficiary for (ID={company_id}).")

            service = CorPayBeneficiaryCacheService()
            service.execute(company_id)

            logging.info(f"Finished cache CorPay Beneficiary for (ID={company_id}).")
            logging.info("Command executed successfully!")

        except Exception as ex:
            logging.error(ex)
