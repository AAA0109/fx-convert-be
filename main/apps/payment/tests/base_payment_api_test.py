from datetime import datetime, timedelta
import json

from django.db.models.signals import post_save
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from typing import List, Tuple

from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.billing.signals.handlers import create_stripe_customer_id_for_company
from main.apps.corpay.models import FXBalanceAccount
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.oems.backend.xover import ensure_queue_table
from main.apps.oems.models.cny import CnyExecution

class BasePaymentAPITest(APITransactionTestCase):

    @classmethod
    def setUpTestData(cls):
        # ensure here

        # ensure queue table global1 by default
        ensure_queue_table()

    def setUp(self) -> None:
        post_save.disconnect(
            receiver=create_stripe_customer_id_for_company, sender=Company)

        _, usd = Currency.create_currency(
            symbol="$", mnemonic="USD", name="US Dollar")
        _, euro = Currency.create_currency(
            symbol="€", mnemonic="EUR", name="EURO")
        _, gbp = Currency.create_currency(
            symbol="£", mnemonic="GBP", name="British Pound Sterling")
        _, ugx = Currency.create_currency(
            symbol="USh", mnemonic="UGX", name="Ugandan Shilling")
        _, php = Currency.create_currency(
            symbol="₱", mnemonic="PHP", name="Philippine Peso")
        _, xof = Currency.create_currency(
            symbol="F.CFA", mnemonic="XOF", name="West African CFA franc")
        self.usd = usd
        self.euro = euro
        self.gbp = gbp
        self.ugx = ugx
        self.php = php
        self.xof = xof

        self.fx_pairs = self.__create_pairs()

        self.company = Company(name="TEST COMPANY 1", currency=self.usd)
        self.company.save()

        self.user: User = User.objects.create_user(
            "email@example.com", "password", company=self.company)
        self.login_jwt(email="email@example.com", password="password")
        self.client.force_authenticate(user=self.user)
        self.corpay_usd_fxbalance = FXBalanceAccount.objects.create(
            description='Standard',
            company=self.company,
            account_number=4321,
            currency=self.usd,
            ledger_balance=100000,
            balance_held=0,
            available_balance=100000,
            client_code=268780,
            client_division_id=0
        )
        self.corpay_eur_fxbalance = FXBalanceAccount.objects.create(
            description='Standard',
            company=self.company,
            account_number=1234,
            currency=self.euro,
            ledger_balance=100000,
            balance_held=0,
            available_balance=100000,
            client_code=268780,
            client_division_id=0
        )
        self.mock_ref_data = {
            'CCY_TYPE': 'Spot',
            'FIXING_TIME': 'MOCK_FIXING_TIME',
            'FIXING_VENUE': 'MOCK_FIXING_VENUE',
            'FIXING_SRC': 'MOCK_FIXING_SRC'
        }
        self.mock_get_exec_config_eurusd_reponse = {
            "id": 568,
            "market": "EURUSD",
            "subaccounts": [
                "DU6108530"
            ],
            "staging": False,
            "default_broker": "CORPAY",
            "default_exec_strat": "MARKET",
            "default_hedge_strat": "SELFDIRECTED",
            "default_algo": "LIQUID_TWAP1",
            "spot_dest": "CORPAY",
            "fwd_dest": "CORPAY",
            "spot_rfq_type": "api",
            "fwd_rfq_type": "api",
            "spot_rfq_dest": "RFQ",
            "fwd_rfq_dest": "RFQ",
            "spot_dest": "CORPAY",
            "fwd_dest": "CORPAY",
            "use_triggers": True,
            "active": True,
            "min_order_size_from": 0.01,
            "max_order_size_from": 5000000,
            "min_order_size_to": 0.01,
            "max_order_size_to": 5000000,
            "max_daily_tickets": 100,
            "max_tenor": "1Y",
            "company": self.company.pk
        }
        self.__create_cny_exec(pairs=self.fx_pairs)
        self.mock_convert_amount = (120.00, InstrumentTypes.SPOT, None)

    def tearDown(self) -> None:
        post_save.connect(
            receiver=create_stripe_customer_id_for_company, sender=Company)


        return super().tearDown()

    def __create_pairs(self):
        pairs = []
        currs = (self.usd, self.euro, self.gbp, self.ugx, self.php, self.xof)
        for curr1 in currs:
            for curr2 in currs:
                _, pair = FxPair.create_fxpair(base=curr1, quote=curr2)
                pairs.append(pair)
        return pairs

    def __create_cny_exec(self, pairs:List[FxPair]):
        for pair in pairs:
            if pair.base_currency != pair.quote_currency:
                fwd_rfq_type = fwd_rfq_type=CnyExecution.RfqTypes.API
                if pair.quote_currency == self.php:
                    fwd_rfq_type = fwd_rfq_type=CnyExecution.RfqTypes.MANUAL
                elif pair.quote_currency == self.xof:
                    fwd_rfq_type = fwd_rfq_type=CnyExecution.RfqTypes.UNSUPPORTED
                cny_exec, created = CnyExecution.objects.get_or_create(
                    company=self.company,
                    fxpair=pair,
                    spot_rfq_type=CnyExecution.RfqTypes.API,
                    fwd_rfq_type=fwd_rfq_type
                )

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
            self.client.credentials(
                HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        return response

    def do_api_call(self, url: str, payload: dict = None, method: str = 'GET') -> Tuple[dict, int]:
        if method == 'GET':
            response: HttpResponse = self.client.get(
                path=url, content_type='application/json')
        elif method == 'POST':
            response: HttpResponse = self.client.post(
                path=url, data=json.dumps(payload), content_type='application/json')
        elif method == 'PUT':
            response: HttpResponse = self.client.put(
                path=url, data=json.dumps(payload), content_type='application/json')
        elif method == 'DELETE':
            response: HttpResponse = self.client.delete(
                path=url, content_type='application/json')
        try:
            return response.json(), response.status_code
        except:
            return None, response.status_code

    def get_best_x_mock(self, market:str='USDEUR', recommend:bool = True) -> dict:
        return {
            'market': market,
            'recommend': recommend,
            'session': 'Weekend',
            'check_back': datetime.now() + timedelta(days=2),
            'execute_before': datetime.now() + timedelta(days=7),
            'unsupported': False
        }
