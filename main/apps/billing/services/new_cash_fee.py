import logging
from typing import Optional, Iterable

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Company
from main.apps.account.models.cashflow import CashFlow
from main.apps.billing.calculators.fee_calculator import FeeCalculatorServiceInterface, DefaultFeeCalculatorService
from main.apps.billing.models.fee import Fee
from main.apps.billing.models import Payment
from main.apps.billing.payments.methods.factory import PaymentsFactory, PaymentsFactory_DB

logger = logging.getLogger(__name__)


class NewCashFeeService(object):
    def __init__(
        self,
        payments_factory: PaymentsFactory = PaymentsFactory_DB(),
        fee_calculator: FeeCalculatorServiceInterface = DefaultFeeCalculatorService()
    ):
        self._payments_factory = payments_factory
        self._fee_calculator = fee_calculator

    def create_and_charge_new_cashflow_fee(self,
                                           spot_fx_cache: SpotFxCache,
                                           cashflow: CashFlow,
                                           due: Optional[Date] = None,
                                           incurred: Optional[Date] = None
                                           ) -> Fee:
        """
        Create a new fee (invoice) for a newly added cashflow and charge it to the customer
        :param spot_fx_cache: SpotFxCache, contains the spot fx rates used to convert to USD amount
        :param due: Date, when is the fee due by
        :param cashflow: Cashflow, the cashflow which generated the fee
        :param incurred: Date (optional), when the fee originated / was incurred, by default we set to Now
        :return: Fee, the newly created (and charged) fee. Raises if there was issue creating the fee,
            otherwise returns the Fee.
        """
        logger.debug("Computing / creating new cashflow fee")
        try:
            fee = self.create_new_cashflow_fee(spot_fx_cache=spot_fx_cache, due=due, cashflow=cashflow,
                                               incurred=incurred)
            logger.debug(f"Done creating new cashflow fee for {fee.company}, amount: {fee.amount}")
        except Exception as e:
            logger.error(f"Error creating new cashflow fee: {e}")
            raise e

        try:
            logger.debug("Getting payment method")
            payment_method = self._payments_factory.get_payment_method(company=cashflow.account.company)
            if not payment_method:
                logger.error(f"No payment method was supplied to this service, can't charge customer.")
                raise Payment.MissingPaymentMethod(company=cashflow.account.company)

            logger.debug("Charging new cashflow fee")
            payment_method.charge_fees(fees=(fee,))

        except Exception as e:
            logger.error(f"Error charging new cashflow fee: {e}")
            raise e

        return fee

    def charge_fees(self, company: Company, fees: Iterable['Fee']):
        try:
            logger.debug("Getting payment method")
            payment_method = self._payments_factory.get_payment_method(company=company)
            if not payment_method:
                logger.error(f"No payment method was supplied to this service, can't charge customer.")
                raise Payment.MissingPaymentMethod(company=company)

            logger.debug("Charging new cashflow fees")
            return payment_method.charge_fees(fees=fees)

        except Exception as e:
            logger.error(f"Error charging new cashflow fees: {e}")
            raise e

    def _create_new_cashflow_fee_from_amount(self,
                                             amount: float,
                                             cashflow: CashFlow,
                                             due: Optional[Date] = None,
                                             incurred: Optional[Date] = None) -> 'Fee':
        """
        Create a new fee (invoice) for a newly added cashflow
        :param amount: float, amount of the fee (Always in USD)
        :param due: Date, when is the fee due by
        :param cashflow: Cashflow, the cashflow which generated the fee
        :param incurred: Date (optional), when the fee originated / was incurred, by default we set to Now
        :return: Fee, the newly created fee
        """
        if not incurred:  # Billed at the very beginning of the day
            incurred = Date.today()
        if not due:
            due = incurred

        fee = Fee(amount=amount, incurred=incurred, due=due, company=cashflow.account.company,
                  fee_type=Fee.FeeType.NEW_CASHFLOW, cashflow=cashflow)
        fee.save()
        return fee

    def create_new_cashflow_fee(self,
                                spot_fx_cache: SpotFxCache,
                                cashflow: CashFlow,
                                due: Optional[Date] = None,
                                incurred: Optional[Date] = None) -> 'Fee':
        """
        Create a new fee (invoice) for a newly added cashflow
        :param spot_fx_cache: SpotFxCache, contains the spot fx rates used to convert to USD amount
        :param due: Date, when is the fee due by
        :param cashflow: Cashflow, the cashflow which generated the fee
        :param incurred: Date (optional), when the fee originated / was incurred, by default we set to Now
        :return: Fee, the newly created fee
        """
        amount = self._get_cashflow_amount_for_fee(cashflow=cashflow, spot_fx_cache=spot_fx_cache,
                                                   incurred=incurred)
        return self._create_new_cashflow_fee_from_amount(amount=amount, due=due, cashflow=cashflow,
                                                         incurred=incurred)

    def _get_cashflow_amount_for_fee(cls,
                                     cashflow: CashFlow,
                                     spot_fx_cache: SpotFxCache,
                                     incurred: Optional[Date] = None) -> float:
        """
        Compute the cashflow amount used to determine the new cashflow fee from a Cashflow object. This is based
        on the spot FX rates at the time of cashflow creation
        :param cashflow: Cashflow, the cashflow obj (may be installment, raw, or recurring)
        :param spot_fx_cache: SpotFxCache, contains the spot fx rates used to convert to USD amount
        :return: float, the amount in USD of cashflow
        """
        company = cashflow.account.company
        if incurred:
            date = incurred
        else:
            date = Date.today()
        aum = cls._fee_calculator.get_last_aum(company=company, date=date)
        fee_tier = cls._fee_calculator.get_fee_tier(company=company, aum=aum)

        amount = 0
        for cf in cashflow.get_hdl_cashflows():
            fee, cash_value = cls._fee_calculator.calculate_new_cashflow_fee(fee_tier=fee_tier,
                                                                             fee_currency=company.currency,
                                                                             cashflow=cf,
                                                                             spot_fx_cache=spot_fx_cache)
            amount += fee

        return amount
