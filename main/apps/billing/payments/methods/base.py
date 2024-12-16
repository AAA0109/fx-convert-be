from abc import ABC, abstractmethod

from main.apps.billing.models import Fee, Sequence
from main.apps.billing.models import Payment
from main.apps.account.models.company import Company

import logging

logger = logging.getLogger(__name__)


class BasePaymentMethod(ABC):
    method: str

    def charge_fees(self, fees: Sequence[Fee]):
        """
        Charge a sequence of fees to some payment method. If sucessful, all fees will be immediately settled. Otherwise
        they will remain in their current (DUE) state.
        This method raises upon failure
        :param fees: Sequence of Fee, the fees to charge (will make 1 charge for total/aggregate amount)
        """
        if len(fees) == 0:
            raise ValueError("You didn't supply any fees")

        company = fees[0].company
        payment_type = fees[0].get_payment_type()

        logger.debug(f"Computing total amount of {len(fees)} fees for {company}")

        # Compute the total fee, and perform validations on the fees
        total_fee = 0
        for fee in fees:
            if fee.company != company:
                raise RuntimeError(f"Cant mix companies. You are trying to charge company {company.get_name()} "
                                   f"for a fee from company {fee.company.get_name()}")

            if fee.get_payment_type() != payment_type:
                raise RuntimeError("You can't mix payment types when paying multiple fees together")

            if fee.is_settled():
                raise RuntimeError(f"You are trying to change company {company.get_name()} for a settled fee")

            if fee.is_waived():
                raise RuntimeError(f"You are tyring to charge company {company.get_name()} for a waived fee")

            total_fee += fee.amount

        # Initiate the payment
        logger.debug(f"Initializing payment, total: {total_fee}")
        payment = Payment(amount=total_fee, method=self.method, payment_type=payment_type,
                          payment_status=Payment.PaymentStatus.INITIATED)
        payment.save()
        logger.debug("Payment saved, now charging fees")
        if total_fee != 0:
            # TODO: Need to re-enable this after new pricing model is defined
            # success = self._charge_fees_for_payment(company=company, payment=payment)
            success = True
        else:
            # If there is nothing to charge, skip the charge step
            logger.warning("The payment was for $0, skipping the charge, will settle the fees")
            success = True

        # Update payment status, and potentially settle all the fees if success
        if success:
            logger.debug(f"Succesfully charged fees, total: {total_fee}")
            payment.payment_status = Payment.PaymentStatus.SUCCESS
            payment.save()
            # Settle all fees
            for fee in fees:
                fee.settle(status=Fee.Status.PAID, payment=payment, datetime=payment.modified)
        else:
            logger.error("Failed to charge fees")
            payment.payment_status = Payment.PaymentStatus.ERROR
            payment.save()
            raise Payment.PaymentChargeFailure(company=company)

    # =================
    # Private
    # =================

    @abstractmethod
    def _charge_fees_for_payment(self,
                                 company: Company,
                                 payment: Payment) -> bool:
        raise NotImplementedError

