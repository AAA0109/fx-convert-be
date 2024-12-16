from typing import List

import django.test.testcases as testcases
from django.db.models.signals import post_save

from main.apps.account.models import Company, Account
from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import Currency, FxPair


class BaseTestCase(testcases.SimpleTestCase):
    databases = '__all__'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):

        self._clean_fxpairs_and_currencies();
        self._setup_currencies()
        self.fx_pairs = self._setup_fxpairs()

        self.company1 = Company.create_company(name="Test Company 1", currency=self.usd)
        self.account11 = Account.create_account(name="Test Account 1", company=self.company1)
        self.account12 = Account.create_account(name="Test Account 2", company=self.company1)

        self.company2 = Company.create_company(name="Test Company 2", currency=self.usd)
        self.account21 = Account.create_account(name="Test Account", company=self.company2)

    def _setup_currencies(self):
        _, usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        _, euro = Currency.create_currency(symbol="€", mnemonic="EUR", name="EURO")
        _, gbp = Currency.create_currency(symbol="£", mnemonic="GBP", name="Great British Pound")
        self.usd = usd
        self.euro = euro
        self.gbp = gbp

    def _setup_fxpairs(self) -> List[FxPair]:
        pairs = []
        currs = (self.usd, self.euro, self.gbp)
        for curr1 in currs:
            for curr2 in currs:
                if curr1 == curr2:
                    continue
                _, pair = FxPair.create_fxpair(base=curr1, quote=curr2)
                pairs.append(pair)
        return pairs

    def tearDown(self):

        if self.account11:
            self.account11.delete()

        if self.account12:
            self.account12.delete()

        if self.account21:
            self.account21.delete()

        self.company1.delete()
        self.company2.delete()

        for pair in self.fx_pairs:
            pair.delete()

        self.usd.delete()
        self.euro.delete()
        self.gbp.delete()


        super().tearDown()

    @classmethod
    def _clean_fxpairs_and_currencies(cls):
        FxPair.objects.all().delete()
        Currency.objects.all().delete()
