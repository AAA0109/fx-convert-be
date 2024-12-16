import logging

from django.core.management.base import BaseCommand, CommandParser
from main.apps.account.models.company import Company
from main.apps.account.services.company import CompanyUtil


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean company data and delete company'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--company_id',
                            type=str,
                            default=None,
                            required=True,
                            help="Company ID"
                            )

    def handle(self, *args, **options):
        company_id = options['company_id']

        if isinstance(company_id, str):
            try:
                company_id = int(company_id)
            except Exception as e:
                logger.error(f"Error executing command: {e}")
                raise e

        try:
            company = Company.objects.get(id=company_id)
            CompanyUtil().clean_all_company_data(company=company)
            logging.info(f"Success removing company with id {company_id}")
        except Company.DoesNotExist:
            logging.error(f"Company with id {company_id} doesn't exist")
        except Exception as e:
            logging.error(f"Error removing company {company.name}: {e}", exc_info=True)
