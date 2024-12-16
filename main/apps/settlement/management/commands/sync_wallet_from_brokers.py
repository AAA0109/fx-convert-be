import logging

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from main.apps.account.models import Company
from main.apps.broker.models import BrokerProviderOption
from main.apps.settlement.services.wallet import WalletServiceFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync wallets from brokers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Specify a company ID to sync wallets for a specific company',
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
                    self.stdout.write(
                        self.style.HTTP_INFO(
                            f"Starting wallet sync for company {company.name} - {company.pk}")
                    )
                    wallet_services = WalletServiceFactory(
                        company).create_wallet_services()
                    for wallet_service in wallet_services:
                        wallet_service.sync_wallets_from_broker()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Wallets successfully synced for company {company.name} - {company.pk}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error syncing wallets for company {company.name} - {company.pk}: {str(e)}')
                    )
                    logger.exception(e)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'An unexpected error occurred: {str(e)}')
            )
