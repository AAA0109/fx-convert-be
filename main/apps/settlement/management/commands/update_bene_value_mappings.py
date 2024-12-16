from django.core.management.base import BaseCommand

from main.apps.settlement.services.beneficiary import BeneficiaryValueMappingService


class Command(BaseCommand):
    help = 'Populates beneficiary field configurations and value mappings'

    def handle(self, *args, **options):
        BeneficiaryValueMappingService.create_or_update_value_mappings()
        self.stdout.write(self.style.SUCCESS('Beneficiary value mappings populated successfully.'))
