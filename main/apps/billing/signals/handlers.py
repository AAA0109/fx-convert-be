from django.db.models.signals import post_save
from django.dispatch import receiver

from main.apps.account.models.company import Company
from main.apps.billing.services.stripe.customer import StripeCustomerService


@receiver(post_save, sender=Company)
def create_stripe_customer_id_for_company(sender, instance, created, **kwargs):
    if created:
        stripe_customer_service = StripeCustomerService()
        stripe_customer_service.create_customer_for_company(instance)
