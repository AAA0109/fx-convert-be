from abc import ABC
from django.conf import settings
from main.apps.account.models import Company

import stripe

stripe.api_key = settings.STRIPE_API_KEY


class StripeCustomerService(ABC):
    def create_customer_for_all_company(self):
        for company in Company.objects.all():
            self.create_customer_for_company(company=company)

    def create_customer_for_company(self, company: Company) -> str:
        if company.stripe_customer_id is not None:
            return company.stripe_customer_id
        if company.account_owner:
            customer_result = stripe.Customer.search(
                query=f"email:'{company.account_owner.email}'"
            )
        else:
            customer_result = None
        if customer_result is not None and len(customer_result.data):
            found_stripe_customer = customer_result.data[0]
            if company.stripe_customer_id != found_stripe_customer.id:
                company.stripe_customer_id = found_stripe_customer.id
                company.save()
        else:
            email = None
            if company.account_owner is not None:
                email = company.account_owner.email
            customer = stripe.Customer.create(
                name=company.name,
                email=email,
                metadata={
                    'pangea_company_id': company.id
                }
            )
            company.stripe_customer_id = customer.id
            company.save()
        return company.stripe_customer_id

    def create_customer(self, customer_data: dict = None) -> stripe.Customer:
        return stripe.Customer.create(**customer_data)

    def delete_customer(self, customer_id: str):
        return stripe.Customer.delete(customer_id)

    def get_customer(self, customer_id: str):
        return stripe.Customer.retrieve(id=customer_id)
