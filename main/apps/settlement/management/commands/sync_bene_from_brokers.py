import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from main.apps.account.models import Company
from main.apps.broker.models import BrokerProviderOption
from main.apps.settlement.services.beneficiary import BeneficiaryServiceFactory
from main.apps.settlement.services.wallet import WalletServiceFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync bene from brokers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            nargs='?',
            default=None,
            type=int,
            help='Optional: Specify a company ID to sync wallets for a specific company',
        )
        parser.add_argument(
            '--broker',
            type=str,
            help='Specify a broker to sync',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        try:
            if company_id:
                companies = Company.objects.filter(pk=company_id)
                if not companies.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f'Company with ID {company_id} not found')
                    )
                    return
            else:
                companies = Company.objects.all()

            for company in companies:
                try:
                    beneficiary_services = BeneficiaryServiceFactory(
                        company).create_beneficiary_services()
                    total_synced = 0
                    for beneficiary_service in beneficiary_services:
                        beneficiaries = beneficiary_service.sync_beneficiaries_from_broker()
                        total_synced += len(beneficiaries)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'{total_synced} Beneficiaries successfully synced for company {company.name} - {company.pk}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error syncing beneficiaries for company {company.name} - {company.pk}: {str(e)}')
                    )
                    if settings.DEBUG:
                        logger.exception(e)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'An unexpected error occurred: {str(e)}')
            )
