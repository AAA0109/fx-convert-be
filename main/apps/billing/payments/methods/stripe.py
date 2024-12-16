import stripe.error

from main.apps.billing.models import Payment, Transaction
from main.apps.billing.payments.methods.base import BasePaymentMethod
from main.apps.billing.services.stripe.payment import StripePaymentService
from main.apps.account.models.company import Company

import numpy as np
import logging

logger = logging.getLogger(__name__)


class StripePaymentMethod(BasePaymentMethod):
    method = 'stripe'

    def __init__(self):
        self._stripe_payment = StripePaymentService()

    def _charge_fees_for_payment(self,
                                 company: Company,
                                 payment: Payment) -> bool:

        setup_intent = self._stripe_payment.retrieve_setup_intent(company.stripe_setup_intent_id)

        try:
            converted_to_cents = int(np.round(100 * payment.amount, 0))
            payment_intent = self._stripe_payment.create_payment_intent(converted_to_cents,
                                                                        company.currency.mnemonic.lower(),
                                                                        setup_intent.customer,
                                                                        setup_intent.payment_method)
            success = True
        except stripe.error.CardError as e:
            err = e.error
            # Error code will be authentication_required if authentication is needed
            logging.error("Error charging fees, Code is: %s" % err.code)
            payment_intent_id = err.payment_intent['id']
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            success = False
        except stripe.error.InvalidRequestError as e:
            err = e.error
            logging.error("Error charging fees, Code is: %s" % err.code)
            return False

        transaction = Transaction(
            txn_id=payment_intent.id,
            payment=payment
        )
        transaction.save()

        return success
