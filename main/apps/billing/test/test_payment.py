from django.db.models.signals import post_save
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import DictSpotFxCache

from main.apps.account.models import CashFlow, Company
from main.apps.billing.models import Fee
from main.apps.billing.services.aum_fee import AumFeeRecorderDB
from main.apps.billing.services.new_cash_fee import NewCashFeeService
from main.apps.core.tests.base import BaseTestCase
from main.apps.billing.payments.methods.stripe import StripePaymentMethod
from main.apps.billing.services.stripe.customer import StripeCustomerService
from main.apps.billing.services.stripe.payment import StripePaymentService, Card


class PaymentTestCase(BaseTestCase):
    stripe_customer_service: StripeCustomerService
    stripe_payment_service: StripePaymentService
    stripe: StripePaymentMethod
    maintenance_fee: Fee
    new_cashflow_fee: Fee

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()


        cls._setup_stripe()
        cls._setup_fees()


    @classmethod
    def _setup_fees(cls):
        fee_creator = NewCashFeeService()
        aum_fee_creator = AumFeeRecorderDB()

        date = Date.now()
        cls.maintenance_fees = [aum_fee_creator.create_maintenance_fee(amount=1000.01, incurred=date, due=date + 10,
                                                                       company=cls.company1)]

        cls.maintenance_fees.append(
            aum_fee_creator.create_maintenance_fee(amount=1000.005, incurred=date + 1, due=date + 10,
                                                   company=cls.company1))
        cls.maintenance_fees.append(
            aum_fee_creator.create_maintenance_fee(amount=1000.4, incurred=date + 2, due=date + 10,
                                                   company=cls.company1))

        cls.new_cashflow_fee = fee_creator._create_new_cashflow_fee_from_amount(amount=1000.5, incurred=date, due=date,
                                                                                cashflow=cls.cashflow1_eur)

    def test_charge_maintenance_fee(self):
        total_fee = 0
        for fee in self.maintenance_fees:
            self.assertEqual(fee.status, Fee.Status.DUE)
            total_fee += fee.amount

        self.stripe.charge_fees(fees=self.maintenance_fees)

        for fee in self.maintenance_fees:
            self.assertEqual(fee.status, Fee.Status.PAID)
            self.assertTrue(fee.is_settled())
            self.assertEqual(fee.payment.amount, total_fee)

    def test_charge_new_cashflow_fee(self):
        self.assertTrue(self.stripe_payment_service.has_setup_intent(company=self.company1))
        self.assertEqual(self.new_cashflow_fee.status, Fee.Status.DUE)
        self.stripe.charge_fees((self.new_cashflow_fee,))
        self.assertEqual(self.new_cashflow_fee.status, Fee.Status.PAID)
        self.assertTrue(self.new_cashflow_fee.is_settled())
        self.assertEqual(self.new_cashflow_fee.payment.amount, self.new_cashflow_fee.amount)

    def test_create_and_charge_new_cashflow_fee(self):
        fee_service = NewCashFeeService()

        spots = DictSpotFxCache(date=Date.create(year=2020, month=1, day=1),
                                spots={'GBP/USD': 1.1,
                                       'EUR/USD': 1.2})
        date = Date.create(year=2020, month=5, day=1)

        # Test raw cashflow
        cashflow = CashFlow.create_cashflow(account=self.account1_1, date=date, currency=self.gbp,
                                            amount=1000, status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

        fee = fee_service.create_and_charge_new_cashflow_fee(spot_fx_cache=spots,
                                                             incurred=date, due=date,
                                                             cashflow=cashflow)

        self.assertEqual(fee.status, Fee.Status.PAID)
        self.assertTrue(fee.is_settled())
        self.assertEqual(fee.payment.amount, fee.amount)
        self.assertEqual(fee.amount, 5.5)

    @classmethod
    def _setup_stripe(cls):
        # Setup stripe customers for each company
        cls.stripe_customer_service = StripeCustomerService()
        for company in (cls.company1, cls.company2):
            cls.stripe_customer_service.create_customer_for_company(company)

        # Retrieve payment intents for each company
        cls.stripe_payment_service = StripePaymentService()
        for company in (cls.company1, cls.company2):
            setup_intent = cls.stripe_payment_service.retrieve_setup_intent_for_company(company)
            if not setup_intent:
                setup_intent = cls.stripe_payment_service.create_setup_intent_for_company_from_payment(
                    company=company,
                    payment_method='pm_card_visa'
                )
            if not company.stripe_setup_intent_id:
                raise Company.MissingStripeSetupIntent(company)
        cls.stripe = StripePaymentMethod()
