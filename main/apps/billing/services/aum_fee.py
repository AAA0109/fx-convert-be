from abc import ABC, abstractmethod
from typing import Optional
import datetime as dt

from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models.company import Company
from main.apps.billing.support.rolling_aum import RollingAum
from main.apps.billing.models.fee import Fee
from main.apps.billing.models.aum import Aum
from main.apps.billing.services.fee import FeeProviderService
from main.apps.billing.calculators.fee_calculator import FeeCalculatorServiceInterface, DefaultFeeCalculatorService
from main.apps.billing.payments.methods.factory import PaymentsFactory, PaymentsFactory_DB

import logging

logger = logging.getLogger(__name__)


class AumFeeRecorder(ABC):
    """
    Interface for recording rolling AUM, and the associated Fee
    """

    @abstractmethod
    def record_rolling_aum(self,
                           date: Date,
                           company: Company,
                           rolling_aum: RollingAum):
        # 1) Update a table which records it (create or update for the day)
        raise NotImplementedError

    @abstractmethod
    def invoice_daily_aum_fee(self, date: Date, due_date: Date, company: Company, day_charge: float):
        raise NotImplementedError


class AumFeeRecorderDB(AumFeeRecorder):
    """
    Fee Recorder attached to the database for recording rolling AUM, and the associated Fee
    """

    def record_rolling_aum(self,
                           date: Date,
                           company: Company,
                           rolling_aum: RollingAum) -> Aum:
        date_ = dt.date(year=date.year, month=date.month, day=date.day)
        aum, created = Aum.objects.update_or_create(
            company=company,
            date=date_,
            defaults={
                'daily_aum': rolling_aum.todays_aum,
                'rolling_aum': rolling_aum.rolling_aum,
                'rolling_window': rolling_aum.window_size,
                'actual_window': rolling_aum.actual_days_in_window,
                'recorded': Date.now()
            }
        )
        return aum

    def invoice_daily_aum_fee(self,
                              date: Date,
                              due_date: Date,
                              company: Company,
                              day_charge: float) -> Fee:
        return self.create_maintenance_fee(amount=day_charge,
                                           due=due_date,
                                           company=company,
                                           incurred=date)

    def create_maintenance_fee(self,
                               amount: float,
                               due: Date,
                               company: Company,
                               incurred: Optional[Date] = None) -> 'Fee':
        """
        Create a new fee (invoice) for account maintenance, tied to the AUM of account
        :param amount: float, amount of the fee (Always in USD)
        :param due: Date, when is the fee due by
        :param company: Company, the company that owes the fee
        :param incurred: Date (optional), when the fee originated / was incurred, by default we set to Now
        :return: Fee, the newly created fee
        """
        if not incurred:
            incurred = Date.now()
        incurred_start = incurred.replace(hour=0, minute=0, second=0, microsecond=0)
        incurred_end = incurred_start + dt.timedelta(days=1)
        fee = Fee.objects.filter(
            incurred__range=(incurred_start, incurred_end),
            company=company
        ).first()
        if fee:
            # Fee exists, update it
            fee.amount = amount
            fee.due = due
            fee.fee_type = Fee.FeeType.MAINTENANCE
            fee.save()
        else:
            # Fee doesn't exist, create it
            fee = Fee(
                incurred=incurred,  # Use original timestamp for accurate recording
                company=company,
                amount=amount,
                due=due,
                fee_type=Fee.FeeType.MAINTENANCE
            )
            fee.save()
        return fee


class AumFeeUpdateService(object):
    """
    Service for running the daily AUM fee assessment for customers. This is mainly to provide EOD functionality
    for billing AUM
    """
    dc = DayCounter_HD()

    def __init__(self,
                 aum_fee_recorder: AumFeeRecorder = AumFeeRecorderDB(),
                 fee_provider: FeeProviderService = FeeProviderService(),
                 payments_factory: PaymentsFactory = PaymentsFactory_DB(),
                 fee_calculator: FeeCalculatorServiceInterface = DefaultFeeCalculatorService()):
        """
        :param aum_fee_recorder: AumFeeRecorder, service responsible for recording / invoicing the fees
        :param fee_provider: FeeProviderService
        :param payments_factory: PaymentsFactory
        """
        self._aum_fee_recorder = aum_fee_recorder
        self._fee_provider = fee_provider
        self._payments_factory = payments_factory
        self._fee_calculator = fee_calculator

    def run_eod(self, company: Company, date: Date, spot_fx_cache: SpotFxCache):
        """
        Run the daily EOD process for assessing an AUM fee for a company
        :param company: Company, the company to bill
        :param date: Date, the date of this EOD (this is when we record the fee as being incurred)
        :param spot_fx_cache: the spot cache used for all fx conversions on date
        """
        logger.debug(f"Running Maintenance (AUM) Fee EOD update for company {company}, date {date}")

        # Step 1): calculate update the AUM for the day
        logger.debug("AUM step 1) Calculating Daily and Rolling Aum")
        today_aum = self._fee_calculator.calculate_daily_aum(date=date, company=company,
                                                             spot_fx_cache=spot_fx_cache)
        rolling_aum = self._fee_calculator.calculate_rolling_aum(date=date, company=company, today_aum=today_aum)

        # Step 2): record the new AUM in database
        logger.debug(f"AUM step 2) Record the new AUM in the database. Rolling AUM = {rolling_aum.rolling_aum}")
        aum = self._aum_fee_recorder.record_rolling_aum(date,
                                                        company=company,
                                                        rolling_aum=rolling_aum)
        logger.debug("Done calculating / recording Aum")

        # Step 3) Compute the daily AUM fee
        try:
            logger.debug("Calculating daily charge")
            day_charge = self._fee_calculator.calculate_aum_day_charge(date, company=company, aum=aum)
            logger.debug(f"Calculated daily charge, {day_charge}.")
        except Exception as e:
            logger.error(f"Error calculating the daily charge for {company}: {e}")
            return

        due_date = self._fee_calculator.get_aum_fee_due_date(date=date, company=company)

        # Step 4): invoice the daily AUM fee
        logger.debug(f"AUM step 4) Invoice the daily AUM fee, due date = {due_date}")
        self._aum_fee_recorder.invoice_daily_aum_fee(date=date,
                                                     due_date=due_date, company=company, day_charge=day_charge)
        logger.debug("Done recording daily charge")

        # Step 5): charge the customer if fees are due (or if they have unpaid fees)
        logger.debug(f"AUM step 5) Charge the customer if fees are due.")
        fees_due = self._fee_provider.get_unpaid_maintenance_fees(company=company, due_on_or_before=date)
        if 0 < len(fees_due):
            logger.debug(f"Company {company.get_name()} has {len(fees_due)} unpaid daily maintenance fees, charging.")
            try:
                payment_method = self._payments_factory.get_payment_method(company=company)
                if not payment_method:
                    logger.error(f"No payment method was supplied to this service, can't charge customer.")
                    raise RuntimeError("no payment method was supplied to this service, can't charge customer")

                logger.debug(f"Charging fee...")
                payment_method.charge_fees(fees=fees_due)

            except Exception as e:
                logger.error(f"Error charging Maintenance fee: {e}")
        else:
            logger.debug(f"Company {company} has no fees due, nothing to charge.")

        logger.debug("Done running EOD for Maintenance fee")
