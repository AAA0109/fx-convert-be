import logging

from django.core.management import BaseCommand

from main.apps.core.models import VendorOauth
from main.apps.corpay.services.confirm_parse import EmailConfirmService


class Command(BaseCommand):
    help = "Django command to Collect trade confirm emails"

    def add_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")

    def handle(self, *args, **options):
        try:
            company_id = options.get("company_id")
            qs = VendorOauth.objects.all()
            if company_id:
                qs = qs.filter(company__id=company_id)

            for oauth in qs:
                EmailConfirmService().fetch_emails_oath(oauth)

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
