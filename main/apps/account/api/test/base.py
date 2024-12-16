from typing import List

from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

import main.libs.pubsub.publisher as pubsub
from main.apps.account.models import User, Company, Account
from main.apps.billing.models import FeeTier
from main.apps.currency.models import Currency, FxPair


class BaseTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        pubsub.init_null({})

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls._clean_fxpairs_and_currencies()

        cls._setup_currencies()
        cls.fx_pairs = cls._setup_fxpairs()

    def setUp(self):

        self.user = User.objects.create_user("email@example.com", "password")
        self._setup_company()
        self.user.company = self.company
        self.user.save()
        self.company.save()
        self.login_jwt(email="email@example.com", password="password")
        self.account = None

    @classmethod
    def _setup_company(cls):
        cls.company = Company.objects.create(name="Test Company 1", currency=cls.usd)
        # setup fee tiers
        tiers = [
            {
                "tier_from": 0,
                "new_cash_fee_rate": 0.005,
                "aum_fee_rate": 0.0108,
                "company": cls.company
            },
            {
                "tier_from": 10000000,
                "new_cash_fee_rate": 0.004,
                "aum_fee_rate": 0.0084,
                "company": cls.company
            },
            {
                "tier_from": 100000000,
                "new_cash_fee_rate": 0.003,
                "aum_fee_rate": 0.006,
                "company": cls.company
            },
            {
                "tier_from": 250000000,
                "new_cash_fee_rate": 0.0025,
                "aum_fee_rate": 0.0048,
                "company": cls.company
            },
            {
                "tier_from": 1000000000,
                "new_cash_fee_rate": 0.001,
                "aum_fee_rate": 0.0024,
                "company": cls.company
            }
        ]
        for tier in tiers:
            FeeTier.objects.create(**tier).save()

    @classmethod
    def _setup_currencies(cls):
        _, usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        _, euro = Currency.create_currency(symbol="€", mnemonic="EUR", name="EURO")
        _, gbp = Currency.create_currency(symbol="£", mnemonic="GBP", name="Great British Pound")
        _, cny = Currency.create_currency(symbol="C", mnemonic="CNY", name="Chinese Yuan")
        cls.usd = usd
        cls.euro = euro
        cls.gbp = gbp
        cls.cny = cny

    @classmethod
    def _setup_fxpairs(cls) -> List[FxPair]:
        pairs = []
        currs = (cls.usd, cls.euro, cls.gbp, cls.cny)
        for curr1 in currs:
            for curr2 in currs:
                if curr1 == curr2:
                    continue
                _, pair = FxPair.create_fxpair(base=curr1, quote=curr2)
                pairs.append(pair)
        return pairs

    def tearDown(self):

        if self.account:
            self.account.delete()
            self.account = None

        if self.company:
            self.company.delete()
            self.company = None

        if self.user:
            self.user.delete()
            self.user = None

        if self.client:
            self.client.logout()

        for pair in self.fx_pairs:
            pair.delete()

        self.usd.delete()
        self.euro.delete()
        self.gbp.delete()
        self.cny.delete()


        super().tearDown()

    def create_default_account(self):
        if not self.account:
            response = self.create_account(
                "Default Account",
                [self.usd.mnemonic, self.euro.mnemonic],
                Account.AccountType.LIVE.name, True)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            id = response.data['id']
            self.account = Account.objects.get(pk=id)

        return self.account

    def create_account(self,
                       account_name: str,
                       currencies: List[str],
                       account_type: str,
                       is_active: bool) -> Response:
        url = reverse('main:account:account-list')
        data = {"account_name": account_name,
                "currencies": currencies,
                "account_type": account_type,
                "is_active": is_active
                }
        response = self.client.post(url, data, format='json')
        return response

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

    @classmethod
    def _clean_fxpairs_and_currencies(cls):
        FxPair.objects.all().delete()
        Currency.objects.all().delete()
