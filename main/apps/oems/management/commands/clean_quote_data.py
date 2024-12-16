import logging

from django.core.management.base import BaseCommand, CommandParser
from main.apps.account.models.company import Company
from main.apps.oems.services.quote import QuoteUtil


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean or empty OEMS quote data'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--company_id',
                            type=str,
                            default=None,
                            required=True,
                            help="Company ID. set to 'all' to clean data for all company'"
                            )

    def handle(self, *args, **options):
        company_id = options['company_id']

        if isinstance(company_id, str) and company_id != 'all':
            try:
                company_id = int(company_id)
            except Exception as e:
                logger.error(f"Error executing command: {e}")
                raise e

        companies = Company.objects.all() if company_id == 'all'\
                        else Company.objects.filter(pk__in=[int(company_id)])

        success = []
        failed = []
        for company in companies:
            try:
                QuoteUtil().clean_quote_data(company=company)
                success.append(company.name)
                logging.info(f"Success cleaning up the quote data for {company.name}")
            except Exception as e:
                failed.append(company.name)
                logging.error(f"Error cleaning up the quote data for {company.name}: {e}",
                              exc_info=True)

        logging.info(f"Success cleaning up the quote data for: {', '.join(success)}")
        logging.info(f"Failed cleaning up the quote data for: {', '.join(failed)}")
