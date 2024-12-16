from abc import ABC, abstractmethod

from main.apps.account.models.company import Company
from main.apps.billing.payments.methods.base import BasePaymentMethod
from main.apps.billing.payments.methods.stripe import StripePaymentMethod


class PaymentsFactory(ABC):
    """
    Inteface used to retrive the payment method for a particular company, e.g. Stripe
    """

    @abstractmethod
    def get_payment_method(self, company: Company) -> BasePaymentMethod:
        raise NotImplementedError


class PaymentsFactory_DB(PaymentsFactory):
    """
    Factory to retreive the payment method for a particular company, e.g. Stripe, which looks up the company
    configuration in the database to determine which payment method to return
    """

    def get_payment_method(self, company: Company) -> BasePaymentMethod:
        if company.stripe_customer_id:
            return StripePaymentMethod()

        raise RuntimeError(f"Stripe is not configured for company: {company.get_name()}")

