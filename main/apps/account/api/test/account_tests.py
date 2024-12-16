import unittest

from django.urls import reverse
from rest_framework import status

from main.apps.account.api.test.base import BaseTestCase
from main.apps.account.models import Account


class AccountTestCase(BaseTestCase):
    def test_account_creation(self):
        account_name = "sisdhlhjzl;asdad"
        currencies = [self.usd.mnemonic, self.euro.mnemonic]
        account_type = Account.AccountType.LIVE.name
        is_active = True
        response = self.create_account(account_name, currencies, account_type, is_active)
        account_id = response.data['id']
        account = Account.objects.get(pk=account_id)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(account.company, self.company)
        self.assertEqual(account.name, account_name)
        self.assertEqual(account.type, Account.AccountType.LIVE)
        self.assertEqual(account.is_active, is_active)
        # account_currencies = AccountCurrency.get_currencies_for_account(account=account)
        # for cny in account_currencies:
        #     self.assertTrue(cny.mnemonic in currencies)

    def test_account_creation_with_invalid_currencies(self):
        account_name = "sisdhlhjzl;asdad"
        currencies = [self.usd.mnemonic, self.euro.mnemonic, "INVALID"]
        account_type = Account.AccountType.LIVE.name
        is_active = True
        response = self.create_account(account_name, currencies, account_type, is_active)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_account_creation_with_invalid_account_type(self):
        account_name = "sisdhlhjzl;asdad"
        currencies = [self.usd.mnemonic, self.euro.mnemonic]
        account_type = "INVALID"
        is_active = True
        response = self.create_account(account_name, currencies, account_type, is_active)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_accounts(self):
        response = self.client.get(reverse('main:account:account-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        response = self.create_account("Test Account",
                                       [self.usd.mnemonic, self.euro.mnemonic],
                                       Account.AccountType.LIVE.name, True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(reverse('main:account:account-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_deactivate_account(self):
        response = self.create_account("Test Account",
                                       [self.usd.mnemonic, self.euro.mnemonic],
                                       Account.AccountType.LIVE.name, True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.put(reverse('main:account:account-deactivate', args=[response.data['id']]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account = Account.objects.get(pk=response.data['id'])
        self.assertEqual(account.is_active, False)

    def test_activate_account(self):
        response = self.create_account("Test Account",
                                       [self.usd.mnemonic, self.euro.mnemonic],
                                       Account.AccountType.LIVE.name, False)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.put(reverse('main:account:account-activate', args=[response.data['id']]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account = Account.objects.get(pk=response.data['id'])
        self.assertEqual(account.is_active, True)


if __name__ == '__main__':
    unittest.main()
