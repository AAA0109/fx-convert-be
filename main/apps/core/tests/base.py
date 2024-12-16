import unittest
from typing import List

from django.conf import settings
from django.db.models import Model
from django.db.models.signals import post_save
from django.test import TestCase
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company, Account, CashFlow, User
from main.apps.billing.signals.handlers import create_stripe_customer_id_for_company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.billing.models import FeeTier
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair


class BaseTestCase(TestCase):
    models_to_delete: List[Model] = []
    usd: Currency
    eur: Currency
    gbp: Currency
    fx_pairs: List[FxPair] = []
    user1: User
    user2: User
    company1: Company
    company2: Company
    account1_1: Account
    account1_2: Account
    account2_1: Account
    cashflow1_gbp: CashFlow
    cashflow1_eur: CashFlow

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        post_save.disconnect(receiver=create_stripe_customer_id_for_company, sender=Company)
        cls._clean_fxpairs_and_currencies()
        cls._setup_currencies()
        cls._setup_fx_pairs()
        cls._setup_users()
        cls._setup_companies()
        cls._setup_accounts()
        cls._setup_broker()
        cls._setup_cashflows()


    @classmethod
    def _setup_currencies(cls):
        _, usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        _, eur = Currency.create_currency(symbol="€", mnemonic="EUR", name="EURO")
        _, gbp = Currency.create_currency(symbol="£", mnemonic="GBP", name="Great British Pound")
        cls.usd = usd
        cls.eur = eur
        cls.gbp = gbp

    @classmethod
    def _setup_fx_pairs(cls):
        currs = (cls.usd, cls.eur, cls.gbp)
        for curr1 in currs:
            for curr2 in currs:
                if curr1 == curr2:
                    continue
                _, pair = FxPair.create_fxpair(base=curr1, quote=curr2)
                cls.fx_pairs.append(pair)

    @classmethod
    def _setup_users(cls):
        cls.user1 = User.objects.create_user(email="user1@test.com", password="AsdfAsdf1234")
        cls.user2 = User.objects.create_user(email="user2@test.com", password="AsdfAsdf1234")

    @classmethod
    def _setup_companies(cls):
        cls.company1 = Company.create_company(name="Test Company 1", currency=cls.usd)
        cls.company2 = Company.create_company(name="Test Company 2", currency=cls.usd)
        cls.company1.account_owner = cls.user1
        cls.company2.account_owner = cls.user2
        cls.company1.save()
        cls.company2.save()
        tiers = [
            {
                "tier_from": 0,
                "new_cash_fee_rate": 0.005,
                "aum_fee_rate": 0.0108,
            },
            {
                "tier_from": 10000000,
                "new_cash_fee_rate": 0.004,
                "aum_fee_rate": 0.0084,
            },
            {
                "tier_from": 100000000,
                "new_cash_fee_rate": 0.003,
                "aum_fee_rate": 0.006,
            },
            {
                "tier_from": 250000000,
                "new_cash_fee_rate": 0.0025,
                "aum_fee_rate": 0.0048,
            },
            {
                "tier_from": 1000000000,
                "new_cash_fee_rate": 0.001,
                "aum_fee_rate": 0.0024,
            }
        ]
        for tier in tiers:
            tier['company'] = cls.company1
            FeeTier.objects.create(**tier).save()
            tier['company'] = cls.company2
            FeeTier.objects.create(**tier).save()

    @classmethod
    def _setup_accounts(cls):
        cls.account1_1 = Account.create_account(name="Test Account 1-1", company=cls.company1)
        cls.account1_2 = Account.create_account(name="Test Account 1-2", company=cls.company1)
        cls.account2_1 = Account.create_account(name="Test Account 2-1", company=cls.company2)

    @classmethod
    def _setup_cashflows(cls):
        date = Date.now()
        cls.cashflow1_gbp = CashFlow.create_cashflow(account=cls.account1_1, date=date, currency=cls.gbp, amount=1000,
                                                     status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        cls.cashflow1_eur = CashFlow.create_cashflow(account=cls.account1_1, date=date, currency=cls.eur, amount=1000,
                                                     status=CashFlow.CashflowStatus.PENDING_ACTIVATION)

    @classmethod
    def _setup_broker(cls):
        cls.broker = Broker(name="IBKR")
        cls.broker.save()

        cls.broker_account1 = BrokerAccount(
            company=cls.company1,
            broker=cls.broker,
            broker_account_name=settings.IB_DAM_FB_TEST_BROKER_ACCOUNT_ID,
            account_type=BrokerAccount.AccountType.LIVE
        )
        cls.broker_account1.save()

    @classmethod
    def _clean_fxpairs_and_currencies(cls):
        FxPair.objects.all().delete()
        Currency.objects.all().delete()


if __name__ == '__main__':
    unittest.main()
