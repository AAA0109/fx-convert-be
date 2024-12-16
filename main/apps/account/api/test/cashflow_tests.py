import unittest
from datetime import datetime

import pytz
from django.db.models.signals import post_save
from django.urls import reverse
from hdlib.DateTime.Date import Date
from rest_framework import status

from main.apps.account.api.test import BaseTestCase
from main.apps.account.models import CashFlow, DraftCashFlow
from main.apps.account.models import User, Company, Account
from main.apps.billing.payments.methods.stripe import StripePaymentMethod
from main.apps.billing.services.stripe.customer import StripeCustomerService
from main.apps.billing.services.stripe.payment import StripePaymentService

email = "user1@test.com"
pwd = "AsdfAsdf1234"


class CashflowTest(BaseTestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.user = User.objects.create_user(email=email, password=pwd)
        cls._setup_company()
        cls.user.company = cls.company
        cls.user.save()
        cls.company.account_owner = cls.user
        cls.company.save()
        cls.account = None

        # Setup Stripe (Note: this is very slow, we only want to do this once for all tests)
        cls._setup_stripe_for_company(company=cls.company)
        cls.company.save()


    @classmethod
    def _setup_stripe_for_company(cls, company: Company):
        # ===============================
        # Stripe Setup to charge cashflow fees
        # ===============================

        # Setup stripe customers for each company
        cls.stripe_customer_service = StripeCustomerService()
        cls.stripe_customer_service.create_customer_for_company(company)

        # Retrieve payment intents for each company
        cls.stripe_payment_service = StripePaymentService()

        # cls.stripe_payment_service.create_card_payment_method(stripe_customer_id=company.stripe_customer_id,
        #                                                       card=Card(number="4242424242424242",
        #                                                                 exp_month=10,
        #                                                                 exp_year=2029,
        #                                                                 cvc="314"))

        setup_intent = cls.stripe_payment_service.retrieve_setup_intent_for_company(company)
        if not setup_intent:
            cls.stripe_payment_service.create_setup_intent_for_company(company)

        # Initialize a stripe instance to handle payments
        cls.stripe = StripePaymentMethod()

        if not company.stripe_setup_intent_id:
            raise Company.MissingStripeSetupIntent(company)

    def setUp(self):
        # Note: Do Not call super setup (it will overwrite the setup created in the setUpTestData class method)
        self.login_jwt(email=email, password=pwd)
        self.create_default_account()

    def tearDown(self):
        pass

    def test_create_cashflow(self):
        response = self.create_cashflow('Test Cashflow', self.usd.mnemonic, 100, Date(2015, 3, 31), 'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CashFlow.objects.count(), 1)
        cashflow = CashFlow.objects.first()
        self.assertEqual(cashflow.account, self.account)
        self.assertEqual(cashflow.currency, self.usd)
        self.assertEqual(cashflow.amount, 100)
        self.assertEqual(cashflow.description, "Test description")
        self.assertEqual(cashflow.status, CashFlow.CashflowStatus.PENDING_ACTIVATION)

    def test_create_cashflow_with_invalid_currency(self):
        response = self.create_cashflow('Test Cashflow', 'INVALID', 100, Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CashFlow.objects.count(), 0)

    def test_get_cashflows(self):
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.create_cashflow('Test Cashflow 2',
                                        self.euro.mnemonic,
                                        -100,
                                        Date(2015, 3, 31),
                                        'Test description 2')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(reverse('main:account:cashflow-list', args=[self.account.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Test Cashflow')
        self.assertEqual(response.data[0]['currency']['mnemonic'], self.usd.mnemonic)
        self.assertEqual(response.data[0]['amount'], 100)
        self.assertEqual(response.data[0]['status'], 'pending_activation')
        self.assertEqual(response.data[0]['date'], '2015-03-31T00:00:00Z')
        self.assertEqual(response.data[0]['description'], 'Test description')
        self.assertEqual(response.data[1]['name'], 'Test Cashflow 2')
        self.assertEqual(response.data[1]['currency']['mnemonic'], self.euro.mnemonic)
        self.assertEqual(response.data[1]['amount'], -100)
        self.assertEqual(response.data[1]['status'], 'pending_activation')
        self.assertEqual(response.data[1]['date'], '2015-03-31T00:00:00Z')
        self.assertEqual(response.data[1]['description'], 'Test description 2')

    def test_update_cashflow(self):
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.client.put(reverse('main:account:cashflow-detail', args=[self.account.id, cashflow.id]), {
            'name': 'Test Cashflow 2',
            'currency': self.euro.mnemonic,
            'amount': -100,
            'pay_date': Date(2015, 3, 31).to_str(fmt='%Y-%m-%dT%H:%M'),
            'description': 'Test description 2',
            'charge': False
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cashflow = CashFlow.objects.get(pk=response.data['id'])
        self.assertEqual(cashflow.name, 'Test Cashflow 2')
        self.assertEqual(cashflow.currency, self.euro)
        self.assertEqual(cashflow.amount, -100)
        self.assertEqual(cashflow.status, CashFlow.CashflowStatus.PENDING_ACTIVATION)
        self.assertEqual(cashflow.date, datetime(2015, 3, 31, tzinfo=pytz.UTC))
        self.assertEqual(cashflow.description, 'Test description 2')

    def test_delete_cashflow(self):
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.client.delete(reverse('main:account:cashflow-detail', args=[self.account.id, cashflow.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cashflow = CashFlow.objects.first()
        self.assertEqual(cashflow.status, CashFlow.CashflowStatus.PENDING_DEACTIVATION)

    def test_create_recurring_cashflow(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_recurring_cashflow(name='Test Recurring Cashflow',
                                                  cny=self.usd.mnemonic,
                                                  amount=100,
                                                  pay_date=Date(2015, 3, 31),
                                                  end_date=Date(2015, 4, 30),
                                                  periodicity=periodicity,
                                                  calendar='NULL_CALENDAR',
                                                  description='asdasd')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CashFlow.objects.count(), 1)
        recurring_cashflow = CashFlow.objects.first()
        self.assertEqual(recurring_cashflow.name, 'Test Recurring Cashflow')
        self.assertEqual(recurring_cashflow.currency, self.usd)
        self.assertEqual(recurring_cashflow.amount, 100)
        self.assertEqual(recurring_cashflow.status, 'pending_activation')
        self.assertEqual(recurring_cashflow.date, datetime(2015, 3, 31, tzinfo=pytz.utc))
        self.assertEqual(recurring_cashflow.description, 'asdasd')
        self.assertEqual(recurring_cashflow.periodicity, periodicity)
        self.assertEqual(recurring_cashflow.calendar, 'NULL_CALENDAR')
        self.assertEqual(recurring_cashflow.end_date, datetime(2015, 4, 30, tzinfo=pytz.utc))

    def test_get_recurring_cashflow(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_recurring_cashflow(name='Test Recurring Cashflow',
                                                  cny=self.usd.mnemonic,
                                                  amount=100,
                                                  pay_date=Date(2015, 3, 31),
                                                  end_date=Date(2015, 4, 30),
                                                  periodicity=periodicity,
                                                  calendar='NULL_CALENDAR',
                                                  description='asdasd')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(reverse('main:account:cashflow-list', args=[self.account.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Recurring Cashflow')
        self.assertEqual(response.data[0]['currency']['mnemonic'], self.usd.mnemonic)
        self.assertEqual(response.data[0]['amount'], 100)
        self.assertEqual(response.data[0]['status'], 'pending_activation')
        self.assertEqual(response.data[0]['date'], '2015-03-31T00:00:00Z')
        self.assertEqual(response.data[0]['description'], 'asdasd')
        self.assertEqual(response.data[0]['periodicity'], periodicity)
        self.assertEqual(response.data[0]['calendar'], 'NULL_CALENDAR')
        self.assertEqual(response.data[0]['end_date'], '2015-04-30T00:00:00Z')

    def test_create_draft(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.create_draft_cashflow(cashflow=cashflow,
                                              name='Test Draft Cashflow',
                                              cny=self.usd.mnemonic,
                                              amount=100,
                                              date=Date(2015, 3, 31),
                                              description='Test description',
                                              periodicity=periodicity,
                                              calendar='NULL_CALENDAR',
                                              end_date=Date(2015, 4, 30))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cashflow_id'], cashflow.id)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft_cashflow = DraftCashFlow.objects.first()
        self.assertEqual(draft_cashflow.name, 'Test Draft Cashflow')
        self.assertEqual(draft_cashflow.currency, self.usd)
        self.assertEqual(draft_cashflow.amount, 100)
        self.assertEqual(draft_cashflow.date, datetime(2015, 3, 31, tzinfo=pytz.utc))
        self.assertEqual(draft_cashflow.description, 'Test description')
        self.assertEqual(draft_cashflow.periodicity, periodicity)
        self.assertEqual(draft_cashflow.calendar, 'NULL_CALENDAR')
        self.assertEqual(draft_cashflow.end_date, datetime(2015, 4, 30, tzinfo=pytz.utc))
        cashflow = CashFlow.objects.first()
        self.assertEqual(cashflow.draft.name, draft_cashflow.name)
        self.assertEqual(cashflow.draft.currency, draft_cashflow.currency)
        self.assertEqual(cashflow.draft.amount, draft_cashflow.amount)
        self.assertEqual(cashflow.draft.date, draft_cashflow.date)
        self.assertEqual(cashflow.draft.description, draft_cashflow.description)
        self.assertEqual(cashflow.draft.periodicity, draft_cashflow.periodicity)
        self.assertEqual(cashflow.draft.calendar, draft_cashflow.calendar)
        self.assertEqual(cashflow.draft.end_date, draft_cashflow.end_date)
        self.assertEqual(cashflow.draft.created, draft_cashflow.created)
        self.assertEqual(cashflow.draft.modified, draft_cashflow.modified)

    def test_update_draft(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.create_draft_cashflow(cashflow=cashflow,
                                              name='Test Draft Cashflow',
                                              cny=self.usd.mnemonic,
                                              amount=100,
                                              date=Date(2015, 3, 31),
                                              description='Test description',
                                              periodicity=periodicity,
                                              calendar='NULL_CALENDAR',
                                              end_date=Date(2015, 4, 30))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft_cashflow = DraftCashFlow.objects.first()
        response = self.create_account("Test Account",
                                       [self.usd.mnemonic, self.euro.mnemonic],
                                       Account.AccountType.LIVE.name, False)
        secondary_account = response.data
        response = self.client.put(
            reverse('main:account:draft-detail', args=[self.account.id, cashflow.id, draft_cashflow.id]), {
                'name': 'Test Cashflow 2',
                'currency': self.euro.mnemonic,
                'amount': -100,
                'date': Date(2015, 3, 31).to_str(fmt='%Y-%m-%dT%H:%M'),
                'description': 'Test description 2',
                'action': 'UPDATE',
                'account_id': secondary_account['id']
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft_cashflow = DraftCashFlow.objects.first()
        self.assertEqual(draft_cashflow.name, 'Test Cashflow 2')
        self.assertEqual(draft_cashflow.currency, self.euro)
        self.assertEqual(draft_cashflow.amount, -100)
        self.assertEqual(draft_cashflow.date, datetime(2015, 3, 31, tzinfo=pytz.utc))
        self.assertEqual(draft_cashflow.description, 'Test description 2')
        self.assertEqual(draft_cashflow.periodicity, None)
        self.assertEqual(draft_cashflow.calendar, None)
        self.assertEqual(draft_cashflow.end_date, None)
        self.assertEqual(draft_cashflow.account_id, secondary_account['id'])

    def test_delete_draft(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.create_draft_cashflow(cashflow=cashflow,
                                              name='Test Draft Cashflow',
                                              cny=self.usd.mnemonic,
                                              amount=100,
                                              date=Date(2015, 3, 31),
                                              description='Test description',
                                              periodicity=periodicity,
                                              calendar='NULL_CALENDAR',
                                              end_date=Date(2015, 4, 30))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        cashflow = CashFlow.objects.first()
        draft = cashflow.draft
        self.assertIsNotNone(draft)
        response = self.client.delete(
            reverse('main:account:draft-detail', args=[self.account.id, cashflow.id, draft.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DraftCashFlow.objects.count(), 0)
        cashflow = CashFlow.objects.first()
        self.assertIsNone(cashflow.draft)

    def test_activate_draft(self):
        periodicity = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE"
        response = self.create_cashflow('Test Cashflow',
                                        self.usd.mnemonic,
                                        100,
                                        Date(2015, 3, 31),
                                        'Test description')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cashflow = CashFlow.objects.first()
        response = self.create_draft_cashflow(cashflow=cashflow,
                                              name='Test Draft Cashflow',
                                              cny=self.usd.mnemonic,
                                              amount=-100,
                                              date=Date(2015, 5, 31),
                                              description='Test description',
                                              periodicity=periodicity,
                                              calendar='NULL_CALENDAR',
                                              end_date=Date(2015, 4, 30))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        cashflow = CashFlow.objects.first()
        draft = cashflow.draft
        r = self.client.put(reverse('main:account:draft-activate', args=[self.account.id, cashflow.id, draft.id]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        cashflow = CashFlow.objects.first()
        self.assertIsNone(cashflow.draft)
        self.assertEqual(cashflow.name, 'Test Draft Cashflow')
        self.assertEqual(cashflow.currency, self.usd)
        self.assertEqual(cashflow.amount, -100)
        self.assertEqual(cashflow.date, Date(2015, 5, 31, tzinfo=pytz.utc))
        self.assertEqual(cashflow.description, 'Test description')
        self.assertEqual(cashflow.periodicity, periodicity)
        self.assertEqual(cashflow.calendar, 'NULL_CALENDAR')
        self.assertEqual(cashflow.end_date, datetime(2015, 4, 30, tzinfo=pytz.utc))

    def create_cashflow(self, name: str, cny: str, amount: float, pay_date: Date, description: str):
        return self.client.post(reverse('main:account:cashflow-list', args=[self.account.id]), {
            'name': name,
            'currency': cny,
            'amount': amount,
            'pay_date': pay_date.to_str(fmt='%Y-%m-%dT%H:%M'),
            'description': description,
            'charge': False
        })

    def create_recurring_cashflow(self,
                                  name: str,
                                  cny: str,
                                  amount: float,
                                  pay_date: Date,
                                  end_date: Date,
                                  periodicity: str,
                                  calendar: str,
                                  description: str):
        return self.client.post(reverse('main:account:cashflow-list', args=[self.account.id]), {
            'name': name,
            'currency': cny,
            'amount': amount,
            'pay_date': pay_date.to_str(fmt='%Y-%m-%dT%H:%M'),
            'description': description,
            'end_date': end_date.to_str(fmt='%Y-%m-%dT%H:%M'),
            'periodicity': periodicity,
            'calendar': calendar,
            'charge': False
        })

    def create_draft_cashflow(self,
                              cashflow,
                              name: str,
                              cny: str,
                              amount: float,
                              date: Date,
                              end_date: Date,
                              periodicity: str,
                              calendar: str,
                              description: str):
        return self.client.post(reverse('main:account:draft-list', args=[self.account.id, cashflow.id]), {
            'name': name,
            'currency': cny,
            'amount': amount,
            'date': date.to_str(fmt='%Y-%m-%dT%H:%M'),
            'end_date': end_date.to_str(fmt='%Y-%m-%dT%H:%M'),
            'periodicity': periodicity,
            'calendar': calendar,
            'description': description,
            'action': 'CREATE'
        })

    def login_jwt(self, email, password):
        token_url = reverse('main:auth:token_obtain_pair')
        response = self.client.post(token_url, {
            "email": email,
            "password": password
        }, format="json")
        if response.status_code == status.HTTP_200_OK:
            token = response.json()
            self.access_token = token['access']
            self.refresh_token = token['refresh']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        return response


if __name__ == '__main__':
    unittest.main()
