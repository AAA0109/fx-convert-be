from django.core.management.base import BaseCommand

from main.apps.settlement.services.beneficiary import BeneficiaryFieldMappingService


class Command(BaseCommand):
    help = 'Populates beneficiary field configurations and value mappings'

    def handle(self, *args, **options):
        BeneficiaryFieldMappingService.create_or_update_beneficiary_field_mappings()
        self.stdout.write(self.style.SUCCESS('Beneficiary field mappings populated successfully.'))
