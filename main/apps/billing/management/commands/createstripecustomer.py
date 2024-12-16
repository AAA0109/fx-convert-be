from django.core.management import BaseCommand

from main.apps.billing.services.stripe.customer import StripeCustomerService

class Command(BaseCommand):
    def handle(self,  *args, **options):
        stripe_customer_service = StripeCustomerService()
        stripe_customer_service.create_customer_for_all_company()
        pass
