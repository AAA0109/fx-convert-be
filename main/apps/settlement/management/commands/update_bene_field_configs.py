from django.core.management.base import BaseCommand

from main.apps.settlement.services.beneficiary import BeneficiaryFieldConfigService


class Command(BaseCommand):
    help = 'Seed beneficiary field configurations'

    def handle(self, *args, **options):
        BeneficiaryFieldConfigService.create_or_update_beneficiary_field_configs()
        self.stdout.write(self.style.SUCCESS('Beneficiary field configurations seeded successfully.'))
