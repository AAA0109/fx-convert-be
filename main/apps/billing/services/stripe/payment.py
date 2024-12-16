from abc import ABC
from typing import Iterable, Optional, Union
from django.conf import settings

import stripe

from main.apps.account.models import Company


class Card(object):
    def __init__(self,
                 number: str,
                 exp_month: int,
                 exp_year: int,
                 cvc: str):
        self.number = str(number)
        self.exp_month = int(exp_month)
        self.exp_year = int(exp_year)
        self.cvc = str(cvc)

    def to_dict(self) -> dict:
        return {"number": self.number,
                "exp_month": self.exp_month,
                "exp_year": self.exp_year,
                "cvc": self.cvc}


class StripePaymentService(ABC):
    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY

    def get_payment_methods(self, stripe_customer_id: str, payment_type: Optional[str] = None):
        return stripe.PaymentMethod.list(customer=stripe_customer_id, type=payment_type)

    def create_card_payment_method(self,
                                   stripe_customer_id: str,
                                   card: Card) -> stripe.PaymentMethod:
        method = stripe.PaymentMethod.create(type="card",
                                             card=card.to_dict())
        return stripe.PaymentMethod.attach(method, customer=stripe_customer_id)

    def create_payment_intent(self,
                              amount: Optional[float] = None,
                              currency: Optional[str] = None,
                              customer_id: Optional[str] = None,
                              payment_method_id: Optional[str] = None) -> stripe.PaymentIntent:
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id
        )
        return stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            payment_method=payment_method_id,
            payment_method_types=['us_bank_account', 'card'],
            off_session=True,
            confirm=True
        )

    def create_setup_intent(self,
                            customer: str = None,
                            payment_method_types: Iterable = (),
                            payment_method_options: Optional[dict] = None,
                            payment_method: Optional[Union[str, stripe.PaymentMethod]] = None) -> stripe.SetupIntent:
        if not payment_method_options:
            payment_method_options = {}

        return stripe.SetupIntent.create(
            customer=customer,
            payment_method_types=payment_method_types,
            payment_method_options=payment_method_options,
            payment_method=payment_method
        )

    def retrieve_setup_intent(self, setup_intent_id: str = None) -> stripe.SetupIntent:
        return stripe.SetupIntent.retrieve(id=setup_intent_id)

    def list_setup_intents(self, customer_id: Optional[str] = None, payment_method: Optional[str] = None):
        return stripe.SetupIntent.list(customer=customer_id, payment_method=payment_method)

    def retrieve_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        return stripe.PaymentMethod.retrieve(payment_method_id)

    def create_setup_intent_for_company(self,
                                        company: Company) -> stripe.SetupIntent:
        # Create intent if no intent id is set and return that intent
        intent = self.create_setup_intent(
            customer=company.stripe_customer_id,
            payment_method_types=['us_bank_account', 'card']
        )
        company.stripe_setup_intent_id = intent.id
        company.save()
        return intent

    def create_setup_intent_for_company_from_payment(self,
                                                     company: Company,
                                                     payment_method: Union[str, stripe.PaymentMethod]) -> stripe.SetupIntent:
        # Create intent if no intent id is set and return that intent
        intent = self.create_setup_intent(
            customer=company.stripe_customer_id,
            payment_method=payment_method
        )
        company.stripe_setup_intent_id = intent.id
        company.save()
        return intent

    def retrieve_setup_intent_for_company(self, company: Company) -> Optional[str]:
        if company.stripe_setup_intent_id is not None:
            return company.stripe_setup_intent_id
        customer_result = stripe.Customer.search(
            query=f"email:'{company.account_owner.email}'"
        )
        if len(customer_result.data):
            found_stripe_customer = customer_result.data[0]
            if company.stripe_customer_id == found_stripe_customer.id:
                setup_intents_result = self.list_setup_intents(customer_id=found_stripe_customer.id)
                for setup_intent in setup_intents_result.data:
                    if setup_intent.payment_method is not None:
                        company.stripe_setup_intent_id = setup_intent.id
                        company.save()
                        return setup_intent.id
        return None

    def has_setup_intent(self, company: Company) -> bool:
        return self.retrieve_setup_intent_for_company(company=company) is not None
